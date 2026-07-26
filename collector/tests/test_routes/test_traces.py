"""Tests for trace listing and detail endpoints."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient


def _make_span(
    trace_id: str = "trace-1",
    span_id: str = "span-1",
    agent_name: str = "test_agent",
    event_type: str = "llm_call",
) -> dict:
    """Create a test span payload."""
    return {
        "trace_id": trace_id,
        "span_id": span_id,
        "agent_name": agent_name,
        "event_type": event_type,
        "started_at": datetime.now(UTC).isoformat(),
        "latency_ms": 100.0,
        "model": "gpt-4o",
        "total_tokens": 100,
        "cost_usd": 0.005,
    }


@pytest.mark.asyncio
async def test_list_traces_empty(client: AsyncClient) -> None:
    """Should return empty list when no traces exist."""
    response = await client.get("/api/v1/traces")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_list_traces(client: AsyncClient) -> None:
    """Should list traces after ingestion."""
    for i in range(3):
        await client.post(
            "/api/v1/spans",
            json={"spans": [_make_span(trace_id=f"trace-{i}", span_id=f"span-{i}")]},
        )

    response = await client.get("/api/v1/traces")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3


@pytest.mark.asyncio
async def test_get_trace_not_found(client: AsyncClient) -> None:
    """Should return 404 for non-existent trace."""
    response = await client.get("/api/v1/traces/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_trace_detail(client: AsyncClient) -> None:
    """Should return trace with spans."""
    await client.post(
        "/api/v1/spans",
        json={
            "spans": [
                _make_span(trace_id="detail-trace", span_id="s1"),
                _make_span(trace_id="detail-trace", span_id="s2", event_type="tool_call"),
            ]
        },
    )

    response = await client.get("/api/v1/traces/detail-trace")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "detail-trace"
    assert len(data["spans"]) == 2


@pytest.mark.asyncio
async def test_get_trace_timeline(client: AsyncClient) -> None:
    """Should return timeline data for a trace."""
    await client.post(
        "/api/v1/spans",
        json={"spans": [_make_span(trace_id="tl-trace", span_id="tl-s1")]},
    )

    response = await client.get("/api/v1/traces/tl-trace/timeline")
    assert response.status_code == 200
    data = response.json()
    assert data["trace_id"] == "tl-trace"
    assert len(data["spans"]) == 1


@pytest.mark.asyncio
async def test_filter_by_agent(client: AsyncClient) -> None:
    """Should filter traces by agent name."""
    await client.post(
        "/api/v1/spans",
        json={"spans": [_make_span(trace_id="t1", span_id="s1", agent_name="agent_a")]},
    )
    await client.post(
        "/api/v1/spans",
        json={"spans": [_make_span(trace_id="t2", span_id="s2", agent_name="agent_b")]},
    )

    response = await client.get("/api/v1/traces?agent_name=agent_a")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "agent_a"


@pytest.mark.asyncio
async def test_filter_by_agent_uses_span_not_trace_name(client: AsyncClient) -> None:
    """Filter must match on Span.agent_name, not Trace.name.

    A single trace with spans from two agents: Trace.name is set to the first
    span's agent ("first_agent"), so filtering by the second agent must still
    return this trace. The old implementation (Trace.name == agent_name) would
    return 0.
    """
    await client.post(
        "/api/v1/spans",
        json={
            "spans": [
                _make_span(trace_id="multi", span_id="s1", agent_name="first_agent"),
                _make_span(trace_id="multi", span_id="s2", agent_name="second_agent"),
            ]
        },
    )

    response = await client.get("/api/v1/traces?agent_name=second_agent")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == "multi"
