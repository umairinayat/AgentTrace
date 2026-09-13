"""Thread-safe event buffer with a batching flusher for trace events.

Durability model
----------------
The queue owns the *retry policy*; :class:`~agenttrace.client.TraceClient` owns
*transport* and the on-disk spill file. A batch travels:

1. ``enqueue`` -- non-blocking, callable from any thread.
2. ``_flush_batch`` -- POSTs to the collector. On failure the batch is put back
   at the *front* of the buffer (order preserved) and the flush interval backs
   off exponentially.
3. After ``max_retries`` consecutive failures the batch is spilled to disk by
   the client so it survives process exit, and is replayed on the next
   successful send.

Events are only ever dropped when the in-memory buffer is full *and* the spill
path is also failing -- and that is logged, never silent.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import threading
from collections import deque
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agenttrace.client import TraceClient

from agenttrace.models import SpanEvent

logger = logging.getLogger(__name__)

# Cap on the exponential backoff between failed flush attempts, in seconds.
MAX_BACKOFF_SECONDS = 60.0


class EventQueue:
    """Buffers span events and flushes them to the collector in batches.

    The buffer is a plain ``deque`` guarded by a ``threading.Lock`` rather than
    an ``asyncio.Queue``. Agent frameworks call into the tracer from worker
    threads (LangChain callbacks, CrewAI workers, thread pools), and an
    ``asyncio.Queue`` is not thread-safe and binds to a single event loop --
    neither of which holds here.
    """

    def __init__(
        self,
        client: TraceClient,
        batch_size: int = 10,
        flush_interval: float = 2.0,
        max_queue_size: int = 10000,
        max_retries: int = 3,
    ) -> None:
        """Initialize the event queue.

        Args:
            client: The HTTP client for sending events to the collector.
            batch_size: Number of events per batch flush.
            flush_interval: Seconds between automatic flushes.
            max_queue_size: Maximum buffered events before dropping new ones.
            max_retries: Consecutive send failures tolerated before a batch is
                spilled to the client's on-disk buffer.
        """
        self._client = client
        self._batch_size = batch_size
        self._flush_interval = flush_interval
        self._max_queue_size = max_queue_size
        self._max_retries = max_retries

        self._buffer: deque[SpanEvent] = deque()
        self._lock = threading.Lock()
        self._flush_task: asyncio.Task[None] | None = None
        self._running = False
        self._consecutive_failures = 0
        self._dropped = 0
        # Start true so the first successful send replays anything a previous
        # process spilled to disk before exiting.
        self._replay_pending = True

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
            with contextlib.suppress(asyncio.CancelledError):
                await self._flush_task
            self._flush_task = None
        await self.flush_all()
        logger.debug("EventQueue stopped, remaining events flushed")

    def enqueue(self, event: SpanEvent) -> bool:
        """Add an event to the buffer without blocking. Safe from any thread.

        Returns True if buffered, False if the buffer is full.
        """
        with self._lock:
            if len(self._buffer) >= self._max_queue_size:
                self._dropped += 1
                logger.warning(
                    "Event buffer full (%d events), dropping span_id=%s (%d dropped total)",
                    self._max_queue_size,
                    event.span_id,
                    self._dropped,
                )
                return False
            self._buffer.append(event)
            return True

    def _take_batch(self) -> list[SpanEvent]:
        """Pop up to ``batch_size`` events off the front of the buffer."""
        with self._lock:
            n = min(self._batch_size, len(self._buffer))
            return [self._buffer.popleft() for _ in range(n)]

    def _return_batch(self, batch: list[SpanEvent]) -> None:
        """Put a failed batch back at the front, preserving emission order."""
        with self._lock:
            capacity = max(0, self._max_queue_size - len(self._buffer))
            if len(batch) > capacity:
                dropped = len(batch) - capacity
                self._dropped += dropped
                logger.warning(
                    "Buffer full while requeuing; dropping %d oldest events", dropped
                )
                batch = batch[dropped:]  # keep the newest events that fit
            self._buffer.extendleft(reversed(batch))

    async def _flush_loop(self) -> None:
        """Background loop that flushes events at regular intervals."""
        while self._running:
            try:
                await asyncio.sleep(self._current_interval())
                await self.flush_all()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error in flush loop")

    def _current_interval(self) -> float:
        """Flush interval, backed off exponentially while sends are failing."""
        if self._consecutive_failures == 0:
            return self._flush_interval
        backoff: float = self._flush_interval * (2**self._consecutive_failures)
        return min(backoff, MAX_BACKOFF_SECONDS)

    async def flush_all(self) -> None:
        """Flush every buffered event, batch after batch.

        Flushing a single batch per interval caps throughput at
        ``batch_size / flush_interval`` events per second; anything faster grows
        the buffer until events are dropped. Stops early if a batch fails so a
        dead collector is not hammered.
        """
        while self.pending_count > 0:
            if not await self._flush_batch():
                return

    async def _flush_batch(self) -> bool:
        """Send one batch. Returns True if it was delivered."""
        batch = self._take_batch()
        if not batch:
            return True

        try:
            await self._client.send_batch(batch)
        except Exception:
            self._consecutive_failures += 1
            logger.warning(
                "Failed to send batch of %d events (attempt %d/%d)",
                len(batch),
                self._consecutive_failures,
                self._max_retries,
                exc_info=True,
            )
            if self._consecutive_failures >= self._max_retries:
                # Hand off to disk so the events survive process exit, and let
                # the in-memory buffer keep accepting new spans.
                self._client.spill_to_disk(batch)
                self._replay_pending = True
                self._consecutive_failures = 0
            else:
                self._return_batch(batch)
            return False

        logger.debug("Flushed %d events to collector", len(batch))
        self._consecutive_failures = 0
        await self._replay_spilled()
        return True

    async def _replay_spilled(self) -> None:
        """Re-send anything spilled to disk, now that the collector is back."""
        if not self._replay_pending:
            return
        # Clear first: a failed replay re-spills and sets the flag again.
        self._replay_pending = False
        try:
            replayed = await self._client.flush_local_buffer()
        except Exception:
            logger.debug("Spill replay failed; will retry", exc_info=True)
            self._replay_pending = True
            return
        if replayed:
            logger.info("Replayed %d spans from the local spill buffer", replayed)

    @property
    def pending_count(self) -> int:
        """Number of events waiting to be flushed."""
        with self._lock:
            return len(self._buffer)

    @property
    def has_spill_pending(self) -> bool:
        """Whether a disk spill may still need replaying to the collector."""
        return self._replay_pending

    @property
    def dropped_count(self) -> int:
        """Number of events dropped because the buffer was full."""
        return self._dropped

    @property
    def is_running(self) -> bool:
        """Whether the background flush loop is currently running."""
        return self._running
