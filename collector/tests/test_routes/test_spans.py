"""Tests for span ingestion endpoint."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from httpx import AsyncClient


def _make_span(trace_id: str = "trace-1", span_id: str = "span-1") -> dict:
    """Create a test span payload."""
    return {
        "trace_id": trace_id,
        "span_id": span_id,
        "agent_name": "test_agent",
        "event_type": "llm_call",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "ended_at": datetime.now(timezone.utc).isoformat(),
        "latency_ms": 150.0,
        "model": "gpt-4o",
        "prompt_tokens": 100,
        "completion_tokens": 50,
        "total_tokens": 150,
        "cost_usd": 0.0075,
        "input_data": {"prompt": "Hello"},
        "output_data": {"response": "Hi there"},
    }


@pytest.mark.asyncio
async def test_ingest_single_span(client: AsyncClient) -> None:
    """Should accept a single span."""
    payload = {"spans": [_make_span()]}
    response = await client.post("/api/v1/spans", json=payload)
    assert response.status_code == 200
    assert response.json()["accepted"] == 1


@pytest.mark.asyncio
async def test_ingest_batch(client: AsyncClient) -> None:
    """Should accept multiple spans."""
    spans = [_make_span(span_id=f"span-{i}") for i in range(5)]
    payload = {"spans": spans}
    response = await client.post("/api/v1/spans", json=payload)
    assert response.status_code == 200
    assert response.json()["accepted"] == 5


@pytest.mark.asyncio
async def test_ingest_creates_trace(client: AsyncClient) -> None:
    """Ingesting a span should auto-create a trace record."""
    payload = {"spans": [_make_span(trace_id="new-trace-1")]}
    await client.post("/api/v1/spans", json=payload)

    response = await client.get("/api/v1/traces/new-trace-1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "new-trace-1"
    assert len(data["spans"]) == 1


@pytest.mark.asyncio
async def test_ingest_empty_batch(client: AsyncClient) -> None:
    """Empty batch should be accepted with 0 count."""
    payload = {"spans": []}
    response = await client.post("/api/v1/spans", json=payload)
    assert response.status_code == 200
    assert response.json()["accepted"] == 0
