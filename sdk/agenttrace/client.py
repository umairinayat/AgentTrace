"""Async HTTP client for sending trace events to the AgentTrace Collector."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

import httpx

from agenttrace.models import BatchSpanRequest, SpanEvent

logger = logging.getLogger(__name__)

# Local SQLite fallback buffer path
_FALLBACK_DIR = Path.home() / ".agenttrace" / "buffer"


class TraceClient:
    """Async HTTP client that sends batched span events to the Collector.

    If the collector is unavailable, events are buffered to a local
    JSON Lines file to prevent data loss.
    """

    def __init__(
        self,
        collector_url: str = "http://localhost:8000",
        timeout: float = 10.0,
        api_key: Optional[str] = None,
    ) -> None:
        """Initialize the trace client.

        Args:
            collector_url: Base URL of the AgentTrace Collector.
            timeout: HTTP request timeout in seconds.
            api_key: Optional API key for authentication.
        """
        self._collector_url = collector_url.rstrip("/")
        self._timeout = timeout
        self._api_key = api_key
        self._client: Optional[httpx.AsyncClient] = None

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
            httpx.HTTPError: If the request fails after fallback buffering.
        """
        if not spans:
            return 0

        batch = BatchSpanRequest(spans=spans)

        try:
            client = await self._get_client()
            response = await client.post(
                "/api/v1/spans",
                content=batch.model_dump_json(),
            )
            response.raise_for_status()
            result = response.json()
            accepted = result.get("accepted", len(spans))
            logger.debug("Collector accepted %d spans", accepted)
            return accepted
        except (httpx.HTTPError, httpx.ConnectError, OSError) as exc:
            logger.warning("Failed to send to collector: %s. Buffering locally.", exc)
            self._buffer_locally(spans)
            return 0

    def _buffer_locally(self, spans: list[SpanEvent]) -> None:
        """Buffer spans to a local JSONL file when collector is unavailable."""
        try:
            _FALLBACK_DIR.mkdir(parents=True, exist_ok=True)
            buffer_file = _FALLBACK_DIR / "pending_spans.jsonl"
            with open(buffer_file, "a", encoding="utf-8") as f:
                for span in spans:
                    f.write(span.model_dump_json() + "\n")
            logger.debug("Buffered %d spans to %s", len(spans), buffer_file)
        except OSError:
            logger.exception("Failed to buffer spans locally")

    async def flush_local_buffer(self) -> int:
        """Send any locally buffered spans to the collector.

        Returns:
            Number of spans successfully flushed.
        """
        buffer_file = _FALLBACK_DIR / "pending_spans.jsonl"
        if not buffer_file.exists():
            return 0

        flushed = 0
        remaining_lines: list[str] = []

        with open(buffer_file, encoding="utf-8") as f:
            lines = f.readlines()

        batch: list[SpanEvent] = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                batch.append(SpanEvent(**data))
            except (json.JSONDecodeError, ValueError):
                logger.warning("Skipping invalid buffered span line")
                continue

        if batch:
            try:
                accepted = await self.send_batch(batch)
                if accepted > 0:
                    flushed = accepted
                else:
                    remaining_lines = [span.model_dump_json() + "\n" for span in batch]
            except Exception:
                remaining_lines = [span.model_dump_json() + "\n" for span in batch]

        # Rewrite buffer with only remaining lines
        if remaining_lines:
            with open(buffer_file, "w", encoding="utf-8") as f:
                f.writelines(remaining_lines)
        elif buffer_file.exists():
            buffer_file.unlink()

        return flushed

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
