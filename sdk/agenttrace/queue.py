"""Non-blocking async event queue with batch flusher for trace events."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from agenttrace.client import TraceClient

from agenttrace.models import SpanEvent

logger = logging.getLogger(__name__)


class EventQueue:
    """Async queue that batches span events and flushes them to the collector.

    Events are queued without blocking the caller. A background coroutine
    periodically flushes batches to the collector via the TraceClient.
    """

    def __init__(
        self,
        client: TraceClient,
        batch_size: int = 10,
        flush_interval: float = 2.0,
        max_queue_size: int = 10000,
    ) -> None:
        """Initialize the event queue.

        Args:
            client: The HTTP client for sending events to the collector.
            batch_size: Number of events per batch flush.
            flush_interval: Seconds between automatic flushes.
            max_queue_size: Maximum queue size before dropping events.
        """
        self._client = client
        self._batch_size = batch_size
        self._flush_interval = flush_interval
        self._queue: asyncio.Queue[SpanEvent] = asyncio.Queue(maxsize=max_queue_size)
        self._flush_task: Optional[asyncio.Task[None]] = None
        self._running = False

    def start(self) -> None:
        """Start the background flush coroutine."""
        if self._running:
            return
        self._running = True
        self._flush_task = asyncio.create_task(self._flush_loop())
        logger.debug("EventQueue flush loop started")

    async def stop(self) -> None:
        """Stop the flush loop and drain remaining events."""
        self._running = False
        if self._flush_task is not None:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        # Drain remaining events
        await self._flush_batch()
        logger.debug("EventQueue stopped, remaining events flushed")

    def enqueue(self, event: SpanEvent) -> bool:
        """Add an event to the queue without blocking.

        Returns True if enqueued, False if queue is full.
        """
        try:
            self._queue.put_nowait(event)
            return True
        except asyncio.QueueFull:
            logger.warning("Event queue full, dropping event span_id=%s", event.span_id)
            return False

    async def _flush_loop(self) -> None:
        """Background loop that flushes events at regular intervals."""
        while self._running:
            try:
                await asyncio.sleep(self._flush_interval)
                await self._flush_batch()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error in flush loop")

    async def _flush_batch(self) -> None:
        """Collect up to batch_size events and send them."""
        batch: list[SpanEvent] = []
        while len(batch) < self._batch_size and not self._queue.empty():
            try:
                event = self._queue.get_nowait()
                batch.append(event)
            except asyncio.QueueEmpty:
                break

        if not batch:
            return

        try:
            await self._client.send_batch(batch)
            logger.debug("Flushed %d events to collector", len(batch))
        except Exception:
            logger.exception("Failed to send batch of %d events", len(batch))
            # Re-enqueue failed events if possible
            for event in batch:
                self.enqueue(event)

    @property
    def pending_count(self) -> int:
        """Number of events waiting to be flushed."""
        return self._queue.qsize()

    @property
    def is_running(self) -> bool:
        """Whether the background flush loop is currently running."""
        return self._running
