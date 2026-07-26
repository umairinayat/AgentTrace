"""Tests for the agents enumeration endpoint."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient


def _span(trace_id: str, span_id: str, agent_name: str) -> dict:
    return {
        "trace_id": trace_id,
        "span_id": span_id,
        "agent_name": agent_name,
        "event_type": "llm_call",
        "started_at": datetime.now(UTC).isoformat(),
    }


@pytest.mark.asyncio
async def test_agents_empty(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/agents")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_agents_lists_all_with_counts(client: AsyncClient) -> None:
    """All agents (uncapped) must be returned with span counts."""
    await client.post(
        "/api/v1/spans",
        json={
            "spans": [
                _span("t1", "s1", "agent_a"),
                _span("t1", "s2", "agent_a"),
                _span("t2", "s3", "agent_b"),
            ]
        },
    )

    resp = await client.get("/api/v1/agents")
    assert resp.status_code == 200
    agents = {a["name"]: a["span_count"] for a in resp.json()}
    assert agents == {"agent_a": 2, "agent_b": 1}
