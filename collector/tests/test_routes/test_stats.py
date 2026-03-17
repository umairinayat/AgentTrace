"""Tests for the stats endpoint."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_stats_empty(client: AsyncClient) -> None:
    """Stats should return zeroes when no data exists."""
    resp = await client.get("/api/v1/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_traces"] == 0
    assert data["total_spans"] == 0
    assert data["total_tokens"] == 0
    assert data["total_cost_usd"] == 0.0
    assert data["avg_latency_ms"] == 0.0
    assert data["avg_cost_per_trace"] == 0.0
    assert data["top_agents"] == []
    assert data["top_models"] == []


@pytest.mark.asyncio
async def test_stats_with_data(client: AsyncClient) -> None:
    """Stats should aggregate data from ingested spans."""
    # Ingest some spans
    spans = {
        "spans": [
            {
                "trace_id": "trace-stats-1",
                "span_id": "span-stats-1",
                "agent_name": "test_agent",
                "event_type": "llm_call",
                "started_at": "2024-01-01T00:00:00Z",
                "latency_ms": 100.0,
                "model": "gpt-4o",
                "total_tokens": 500,
                "cost_usd": 0.01,
            },
            {
                "trace_id": "trace-stats-1",
                "span_id": "span-stats-2",
                "agent_name": "test_agent",
                "event_type": "tool_end",
                "started_at": "2024-01-01T00:00:01Z",
                "latency_ms": 50.0,
            },
        ]
    }
    resp = await client.post("/api/v1/spans", json=spans)
    assert resp.status_code == 200

    resp = await client.get("/api/v1/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_traces"] == 1
    assert data["total_spans"] == 2
    assert data["total_tokens"] == 500
    assert len(data["top_agents"]) == 1
    assert data["top_agents"][0]["name"] == "test_agent"
