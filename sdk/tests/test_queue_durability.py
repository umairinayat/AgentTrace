"""Tests for EventQueue durability: full drain, retry, spill, and replay.

These cover the delivery guarantees rather than the mechanics in
``test_queue.py`` -- what happens when the collector is slow, down, or comes
back, and when spans arrive from more than one thread.
"""

from __future__ import annotations

import threading

import pytest

from agenttrace.models import SpanEvent
from agenttrace.queue import EventQueue


def _span(name: str = "test") -> SpanEvent:
    return SpanEvent(agent_name=name, event_type="llm_call")


class FakeClient:
    """Stand-in TraceClient recording sends, spills, and replays."""

    def __init__(self, fail_times: int = 0) -> None:
        self.sent: list[SpanEvent] = []
        self.spilled: list[SpanEvent] = []
        self.fail_times = fail_times
        self.send_calls = 0
        self.replay_calls = 0

    async def send_batch(self, spans: list[SpanEvent]) -> int:
        self.send_calls += 1
        if self.send_calls <= self.fail_times:
            raise ConnectionError("collector unreachable")
        self.sent.extend(spans)
        return len(spans)

    def spill_to_disk(self, spans: list[SpanEvent]) -> bool:
        self.spilled.extend(spans)
        return True

    async def flush_local_buffer(self) -> int:
        self.replay_calls += 1
        replayed = len(self.spilled)
        self.sent.extend(self.spilled)
        self.spilled.clear()
        return replayed


class TestFullDrain:
    """flush_all must not cap throughput at one batch per interval."""

    @pytest.mark.asyncio
    async def test_flush_all_drains_more_than_one_batch(self) -> None:
        client = FakeClient()
        queue = EventQueue(client=client, batch_size=10)  # type: ignore[arg-type]

        for _ in range(35):
            queue.enqueue(_span())

        await queue.flush_all()

        assert queue.pending_count == 0
        assert len(client.sent) == 35
        assert client.send_calls == 4  # 10 + 10 + 10 + 5

    @pytest.mark.asyncio
    async def test_flush_all_stops_on_failure(self) -> None:
        """A dead collector must not be hammered batch after batch."""
        client = FakeClient(fail_times=99)
        queue = EventQueue(client=client, batch_size=10, max_retries=99)  # type: ignore[arg-type]

        for _ in range(35):
            queue.enqueue(_span())

        await queue.flush_all()

        assert client.send_calls == 1
        assert queue.pending_count == 35  # failed batch was returned


class TestRetryAndSpill:
    """Failed batches are retried in memory, then persisted to disk."""

    @pytest.mark.asyncio
    async def test_failed_batch_is_requeued_in_order(self) -> None:
        client = FakeClient(fail_times=1)
        queue = EventQueue(client=client, batch_size=10, max_retries=3)  # type: ignore[arg-type]

        first, second = _span("first"), _span("second")
        queue.enqueue(first)
        queue.enqueue(second)

        await queue._flush_batch()  # fails, batch goes back to the front
        assert queue.pending_count == 2

        await queue._flush_batch()  # succeeds
        assert [s.span_id for s in client.sent] == [first.span_id, second.span_id]

    @pytest.mark.asyncio
    async def test_spills_to_disk_after_max_retries(self) -> None:
        client = FakeClient(fail_times=99)
        queue = EventQueue(client=client, batch_size=10, max_retries=2)  # type: ignore[arg-type]
        queue.enqueue(_span())

        await queue._flush_batch()
        assert queue.pending_count == 1  # retry 1: back in memory
        assert client.spilled == []

        await queue._flush_batch()
        assert queue.pending_count == 0  # retry 2: handed to disk
        assert len(client.spilled) == 1

    @pytest.mark.asyncio
    async def test_backoff_grows_then_resets(self) -> None:
        client = FakeClient(fail_times=2)
        queue = EventQueue(client=client, batch_size=10, flush_interval=2.0, max_retries=5)  # type: ignore[arg-type]
        assert queue._current_interval() == 2.0

        queue.enqueue(_span())
        await queue._flush_batch()
        assert queue._current_interval() == 4.0

        await queue._flush_batch()
        assert queue._current_interval() == 8.0

        await queue._flush_batch()  # succeeds
        assert queue._current_interval() == 2.0


class TestSpillReplay:
    """Spans spilled to disk are re-sent once the collector is reachable."""

    @pytest.mark.asyncio
    async def test_replays_spill_on_next_success(self) -> None:
        client = FakeClient(fail_times=1)
        queue = EventQueue(client=client, batch_size=10, max_retries=1)  # type: ignore[arg-type]

        spilled_span = _span("spilled")
        queue.enqueue(spilled_span)
        await queue._flush_batch()  # fails -> spilled immediately (max_retries=1)
        assert len(client.spilled) == 1

        queue.enqueue(_span("later"))
        await queue._flush_batch()  # succeeds -> triggers replay

        assert client.spilled == []
        assert spilled_span.span_id in {s.span_id for s in client.sent}

    @pytest.mark.asyncio
    async def test_first_success_replays_previous_process_spill(self) -> None:
        """A spill left by an earlier run is picked up without a failure first."""
        client = FakeClient()
        client.spilled.append(_span("from_last_run"))
        queue = EventQueue(client=client, batch_size=10)  # type: ignore[arg-type]

        queue.enqueue(_span("current"))
        await queue._flush_batch()

        assert client.replay_calls == 1
        assert len(client.sent) == 2

    @pytest.mark.asyncio
    async def test_replay_is_not_retried_every_flush(self) -> None:
        client = FakeClient()
        queue = EventQueue(client=client, batch_size=10)  # type: ignore[arg-type]

        queue.enqueue(_span())
        await queue._flush_batch()
        queue.enqueue(_span())
        await queue._flush_batch()

        assert client.replay_calls == 1


class TestThreadSafety:
    """Spans arrive from framework worker threads, not just the event loop."""

    def test_concurrent_enqueue_loses_nothing(self) -> None:
        client = FakeClient()
        queue = EventQueue(client=client, batch_size=10, max_queue_size=10000)  # type: ignore[arg-type]

        def producer() -> None:
            for _ in range(200):
                queue.enqueue(_span())

        threads = [threading.Thread(target=producer) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert queue.pending_count == 1600

    def test_enqueue_needs_no_event_loop(self) -> None:
        """Buffering must work from plain sync code (LangChain's .invoke())."""
        client = FakeClient()
        queue = EventQueue(client=client)  # type: ignore[arg-type]
        assert queue.enqueue(_span()) is True
        assert queue.pending_count == 1


class TestOverflow:
    """The buffer is bounded, and drops are counted rather than silent."""

    def test_drops_are_counted(self) -> None:
        client = FakeClient()
        queue = EventQueue(client=client, max_queue_size=2)  # type: ignore[arg-type]

        assert queue.enqueue(_span()) is True
        assert queue.enqueue(_span()) is True
        assert queue.enqueue(_span()) is False
        assert queue.dropped_count == 1

    @pytest.mark.asyncio
    async def test_requeue_keeps_newest_when_full(self) -> None:
        client = FakeClient(fail_times=99)
        queue = EventQueue(client=client, batch_size=2, max_queue_size=3, max_retries=99)  # type: ignore[arg-type]

        batch = [_span("a"), _span("b")]
        for s in batch:
            queue.enqueue(s)
        await queue._flush_batch()  # takes both, fails, returns both

        assert queue.pending_count == 2
        assert queue.dropped_count == 0
