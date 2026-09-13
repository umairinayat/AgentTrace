"""Tests for TraceClient transport failure reporting and the on-disk spill buffer."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from agenttrace.client import TraceClient
from agenttrace.models import SpanEvent


def _span(name: str = "test") -> SpanEvent:
    return SpanEvent(agent_name=name, event_type="llm_call")


@pytest.fixture
def client(tmp_path: Path) -> TraceClient:
    """Client whose spill buffer is isolated to a temp dir, not $HOME."""
    return TraceClient(collector_url="http://localhost:8000", buffer_dir=tmp_path)


class TestSendBatchRaises:
    """send_batch reports failure to the queue instead of swallowing it."""

    @pytest.mark.asyncio
    async def test_connection_error_propagates(
        self, client: TraceClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def boom(*args: object, **kwargs: object) -> None:
            raise httpx.ConnectError("refused")

        transport_client = await client._get_client()
        monkeypatch.setattr(transport_client, "post", boom)

        with pytest.raises(httpx.ConnectError):
            await client.send_batch([_span()])

        # Transport does not spill on its own -- that is the queue's decision.
        assert not (client._buffer_file).exists()

    @pytest.mark.asyncio
    async def test_http_error_status_propagates(
        self, client: TraceClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def server_error(*args: object, **kwargs: object) -> httpx.Response:
            return httpx.Response(500, request=httpx.Request("POST", "http://x/api/v1/spans"))

        transport_client = await client._get_client()
        monkeypatch.setattr(transport_client, "post", server_error)

        with pytest.raises(httpx.HTTPStatusError):
            await client.send_batch([_span()])

    @pytest.mark.asyncio
    async def test_empty_batch_is_a_noop(self, client: TraceClient) -> None:
        assert await client.send_batch([]) == 0


class TestSpillToDisk:
    """Spans handed to the spill buffer survive on disk."""

    def test_spill_then_read_back(self, client: TraceClient) -> None:
        span = _span("spilled")
        assert client.spill_to_disk([span]) is True

        buffer_file = client._buffer_file
        assert buffer_file.exists()
        recovered = TraceClient._read_spans(buffer_file)
        assert len(recovered) == 1
        assert recovered[0].span_id == span.span_id
        assert recovered[0].agent_name == "spilled"

    def test_spill_appends(self, client: TraceClient) -> None:
        client.spill_to_disk([_span()])
        client.spill_to_disk([_span()])
        assert len(TraceClient._read_spans(client._buffer_file)) == 2

    def test_spill_respects_size_cap(
        self, client: TraceClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A collector that never returns must not fill the disk."""
        monkeypatch.setattr("agenttrace.client.MAX_BUFFER_BYTES", 10)
        assert client.spill_to_disk([_span()]) is True  # first write creates the file
        assert client.spill_to_disk([_span()]) is False  # now over the cap

    def test_corrupt_lines_are_skipped(self, client: TraceClient) -> None:
        client.spill_to_disk([_span("good")])
        with open(client._buffer_file, "a", encoding="utf-8") as f:
            f.write("{not json\n")
            f.write("\n")

        recovered = TraceClient._read_spans(client._buffer_file)
        assert len(recovered) == 1
        assert recovered[0].agent_name == "good"


class TestFlushLocalBuffer:
    """The spill buffer is actually drained -- the bug this whole path exists for."""

    @pytest.mark.asyncio
    async def test_no_buffer_is_a_noop(self, client: TraceClient) -> None:
        assert await client.flush_local_buffer() == 0

    @pytest.mark.asyncio
    async def test_replays_and_deletes_buffer(
        self, client: TraceClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        sent: list[list[SpanEvent]] = []

        async def capture(spans: list[SpanEvent]) -> int:
            sent.append(spans)
            return len(spans)

        client.spill_to_disk([_span("a"), _span("b")])
        monkeypatch.setattr(client, "send_batch", capture)

        assert await client.flush_local_buffer() == 2
        assert len(sent[0]) == 2
        assert not client._buffer_file.exists()

    @pytest.mark.asyncio
    async def test_large_backlog_is_chunked(
        self, client: TraceClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A big backlog must not be posted as one oversized body."""
        monkeypatch.setattr("agenttrace.client.REPLAY_CHUNK_SIZE", 100)
        client.spill_to_disk([_span() for _ in range(250)])

        chunk_sizes: list[int] = []

        async def capture(spans: list[SpanEvent]) -> int:
            chunk_sizes.append(len(spans))
            return len(spans)

        monkeypatch.setattr(client, "send_batch", capture)

        assert await client.flush_local_buffer() == 250
        assert chunk_sizes == [100, 100, 50]

    @pytest.mark.asyncio
    async def test_partial_failure_respills_remainder(
        self, client: TraceClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("agenttrace.client.REPLAY_CHUNK_SIZE", 100)
        client.spill_to_disk([_span() for _ in range(250)])

        calls = {"n": 0}

        async def fail_on_second(spans: list[SpanEvent]) -> int:
            calls["n"] += 1
            if calls["n"] == 2:
                raise httpx.ConnectError("dropped mid-replay")
            return len(spans)

        monkeypatch.setattr(client, "send_batch", fail_on_second)

        with pytest.raises(httpx.ConnectError):
            await client.flush_local_buffer()

        # The 100 that were delivered are gone; the other 150 are still on disk.
        assert len(TraceClient._read_spans(client._buffer_file)) == 150

    @pytest.mark.asyncio
    async def test_concurrent_appends_are_not_lost(
        self, client: TraceClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Spans spilled *during* a replay must survive it.

        The buffer is claimed by rename before reading, so a concurrent spill
        lands in a fresh file rather than being truncated away.
        """
        client.spill_to_disk([_span("original")])

        async def send_and_race(spans: list[SpanEvent]) -> int:
            # Simulates another thread spilling while the replay is in flight.
            client.spill_to_disk([_span("arrived_during_replay")])
            return len(spans)

        monkeypatch.setattr(client, "send_batch", send_and_race)

        assert await client.flush_local_buffer() == 1

        survivors = TraceClient._read_spans(client._buffer_file)
        assert [s.agent_name for s in survivors] == ["arrived_during_replay"]
