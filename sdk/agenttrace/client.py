"""Async HTTP client for sending trace events to the AgentTrace Collector.

This module is pure transport plus an on-disk spill buffer. It deliberately
does *not* implement retry: :class:`~agenttrace.queue.EventQueue` owns that
policy, so ``send_batch`` reports failure by raising rather than swallowing it.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import httpx

from agenttrace.models import BatchSpanRequest, SpanEvent

logger = logging.getLogger(__name__)

# Local JSONL fallback buffer, drained by flush_local_buffer().
_FALLBACK_DIR = Path.home() / ".agenttrace" / "buffer"
_BUFFER_NAME = "pending_spans.jsonl"

# Refuse to grow the spill file without bound if the collector never comes back.
MAX_BUFFER_BYTES = 64 * 1024 * 1024  # 64 MiB

# Spans per request when replaying the spill file, so a large backlog is not
# sent as one enormous body (the collector caps batches at 1000).
REPLAY_CHUNK_SIZE = 500


class TraceClient:
    """Async HTTP client that sends batched span events to the Collector.

    If the collector is unavailable the caller may hand the batch to
    :meth:`spill_to_disk`, which appends it to a local JSON Lines file.
    :meth:`flush_local_buffer` replays that file once the collector is back.
    """

    def __init__(
        self,
        collector_url: str = "http://localhost:8000",
        timeout: float = 10.0,
        api_key: str | None = None,
        buffer_dir: Path | None = None,
    ) -> None:
        """Initialize the trace client.

        Args:
            collector_url: Base URL of the AgentTrace Collector.
            timeout: HTTP request timeout in seconds.
            api_key: Optional API key for authentication.
            buffer_dir: Directory for the on-disk spill buffer. Defaults to
                ``~/.agenttrace/buffer``.
        """
        self._collector_url = collector_url.rstrip("/")
        self._timeout = timeout
        self._api_key = api_key
        self._buffer_dir = buffer_dir or _FALLBACK_DIR
        self._client: httpx.AsyncClient | None = None

    @property
    def _buffer_file(self) -> Path:
        return self._buffer_dir / _BUFFER_NAME

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the async HTTP client."""
        if self._client is None or self._client.is_closed:
            headers: dict[str, str] = {"Content-Type": "application/json"}
            if self._api_key:
                headers["Authorization"] = f"Bearer {self._api_key}"
            self._client = httpx.AsyncClient(
                base_url=self._collector_url,
                timeout=self._timeout,
                headers=headers,
            )
        return self._client

    async def send_batch(self, spans: list[SpanEvent]) -> int:
        """Send a batch of span events to the collector.

        Args:
            spans: List of SpanEvent objects to send.

        Returns:
            Number of accepted spans.

        Raises:
            httpx.HTTPError: If the request fails. The caller (EventQueue) is
                responsible for retrying or spilling the batch to disk.
        """
        if not spans:
            return 0

        batch = BatchSpanRequest(spans=spans)

        client = await self._get_client()
        response = await client.post(
            "/api/v1/spans",
            content=batch.model_dump_json(),
        )
        response.raise_for_status()
        result = response.json()
        accepted = int(result.get("accepted", len(spans)))
        logger.debug("Collector accepted %d spans", accepted)
        return accepted

    def spill_to_disk(self, spans: list[SpanEvent]) -> bool:
        """Append spans to the local JSONL buffer when the collector is down.

        Returns True if the spans were persisted.
        """
        if not spans:
            return True
        try:
            self._buffer_dir.mkdir(parents=True, exist_ok=True)
            buffer_file = self._buffer_file
            if buffer_file.exists() and buffer_file.stat().st_size >= MAX_BUFFER_BYTES:
                logger.error(
                    "Local spill buffer at capacity (%d bytes); dropping %d spans",
                    MAX_BUFFER_BYTES,
                    len(spans),
                )
                return False
            with open(buffer_file, "a", encoding="utf-8") as f:
                for span in spans:
                    f.write(span.model_dump_json() + "\n")
            logger.debug("Spilled %d spans to %s", len(spans), buffer_file)
            return True
        except OSError:
            logger.exception("Failed to spill spans to disk")
            return False

    async def flush_local_buffer(self) -> int:
        """Replay locally spilled spans to the collector.

        The buffer file is first renamed to a private claim file, so spans
        appended concurrently (by another thread or process) land in a fresh
        buffer and cannot be lost when the claim is deleted. Anything that
        fails to send is spilled back.

        Returns:
            Number of spans successfully flushed.
        """
        buffer_file = self._buffer_file
        if not buffer_file.exists():
            return 0

        claim_file = buffer_file.with_suffix(f".{os.getpid()}.claim")
        try:
            buffer_file.rename(claim_file)
        except OSError:
            logger.debug("Could not claim spill buffer; another flush may hold it")
            return 0

        spans = self._read_spans(claim_file)
        if not spans:
            claim_file.unlink(missing_ok=True)
            return 0

        flushed = 0
        try:
            for i in range(0, len(spans), REPLAY_CHUNK_SIZE):
                chunk = spans[i : i + REPLAY_CHUNK_SIZE]
                await self.send_batch(chunk)
                flushed += len(chunk)
        except Exception:
            # Put the unsent remainder back so the next attempt retries it.
            self.spill_to_disk(spans[flushed:])
            claim_file.unlink(missing_ok=True)
            raise

        claim_file.unlink(missing_ok=True)
        return flushed

    @staticmethod
    def _read_spans(path: Path) -> list[SpanEvent]:
        """Parse spans from a JSONL buffer file, skipping corrupt lines."""
        spans: list[SpanEvent] = []
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        spans.append(SpanEvent(**json.loads(line)))
                    except (json.JSONDecodeError, ValueError, TypeError):
                        logger.warning("Skipping invalid buffered span line")
        except OSError:
            logger.exception("Failed to read spill buffer %s", path)
        return spans

    async def health_check(self) -> bool:
        """Check if the collector is reachable."""
        try:
            client = await self._get_client()
            response = await client.get("/api/v1/health")
            return response.status_code == 200
        except (httpx.HTTPError, OSError):
            return False

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
