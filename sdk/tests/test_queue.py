"""Tests for the async event queue."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from agenttrace.models import SpanEvent
from agenttrace.queue import EventQueue


class TestEventQueue:
    """Tests for EventQueue behavior."""

    def test_enqueue(self) -> None:
        """Events should be enqueued without blocking."""
        client = AsyncMock()
        queue = EventQueue(client=client, batch_size=5)

        event = SpanEvent(agent_name="test", event_type="llm_call")
        result = queue.enqueue(event)
        assert result is True
        assert queue.pending_count == 1

    def test_enqueue_full_queue(self) -> None:
        """Enqueue should return False when queue is full."""
        client = AsyncMock()
        queue = EventQueue(client=client, batch_size=5, max_queue_size=2)

        e1 = SpanEvent(agent_name="test", event_type="llm_call")
        e2 = SpanEvent(agent_name="test", event_type="llm_call")
        e3 = SpanEvent(agent_name="test", event_type="llm_call")

        assert queue.enqueue(e1) is True
        assert queue.enqueue(e2) is True
        assert queue.enqueue(e3) is False

    @pytest.mark.asyncio
    async def test_flush_batch(self) -> None:
        """Flush should send queued events to client."""
        client = AsyncMock()
        client.send_batch = AsyncMock(return_value=2)
        queue = EventQueue(client=client, batch_size=10)

        queue.enqueue(SpanEvent(agent_name="test", event_type="llm_call"))
        queue.enqueue(SpanEvent(agent_name="test", event_type="tool_call"))

        await queue._flush_batch()

        client.send_batch.assert_called_once()
        args = client.send_batch.call_args[0][0]
        assert len(args) == 2
        assert queue.pending_count == 0

    @pytest.mark.asyncio
    async def test_stop_drains_queue(self) -> None:
        """Stopping the queue should flush remaining events."""
        client = AsyncMock()
        client.send_batch = AsyncMock(return_value=1)
        queue = EventQueue(client=client, batch_size=10)

        queue.enqueue(SpanEvent(agent_name="test", event_type="llm_call"))
        queue.start()

        await queue.stop()

        client.send_batch.assert_called()
