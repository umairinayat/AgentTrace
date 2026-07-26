"""Tests for the drift endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from httpx import AsyncClient


def _make_alert(
    agent_name: str = "test_agent",
    alert_type: str = "semantic",
    score: float = 0.42,
) -> dict:
    """Create a drift alert payload as the detector would post it."""
    return {
        "agent_name": agent_name,
        "detected_at": datetime.now(timezone.utc).isoformat(),
        "alert_type": alert_type,
        "severity": "warning",
        "score": score,
        "threshold": 0.15,
        "description": "Semantic drift detected",
    }


def _make_baseline(agent_name: str = "test_agent") -> dict:
    """Create a baseline payload as the detector would post it."""
    return {
        "agent_name": agent_name,
        "n_samples": 10,
        "avg_response_length": 120.0,
        "avg_latency_ms": 250.0,
        "avg_token_count": 80.0,
        "embedding_centroid": [0.1, 0.2, 0.3],
        "response_length_distribution": [100.0, 140.0],
        "tool_call_distribution": {"search": 0.7, "calc": 0.3},
    }


@pytest.mark.asyncio
async def test_drift_alerts_empty(client: AsyncClient) -> None:
    """Should return empty list when no alerts exist."""
    resp = await client.get("/api/v1/drift/alerts")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_drift_baseline_not_found(client: AsyncClient) -> None:
    """Should 404 when no baseline exists for agent."""
    resp = await client.get("/api/v1/drift/baseline/nonexistent_agent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_rebuild_baseline(client: AsyncClient) -> None:
    """Rebuild endpoint should queue a request and return ok."""
    resp = await client.post("/api/v1/drift/baseline/test_agent/rebuild")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"

    # The rebuild request should now be pending for the detector to consume.
    pending = await client.get("/api/v1/drift/rebuild-requests")
    assert pending.status_code == 200
    assert any(r["agent_name"] == "test_agent" for r in pending.json())


@pytest.mark.asyncio
async def test_post_alerts_persist_and_are_listed(client: AsyncClient) -> None:
    """Posted alerts must land in the collector and be returned by GET /drift/alerts."""
    resp = await client.post("/api/v1/drift/alerts", json=[_make_alert(agent_name="a1")])
    assert resp.status_code == 200
    assert resp.json() == {"accepted": 1}

    listed = await client.get("/api/v1/drift/alerts")
    assert listed.status_code == 200
    alerts = listed.json()
    assert len(alerts) == 1
    assert alerts[0]["agent_name"] == "a1"
    assert alerts[0]["alert_type"] == "semantic"
    assert alerts[0]["resolved"] == 0


@pytest.mark.asyncio
async def test_post_alerts_dedupes_identical_unresolved(client: AsyncClient) -> None:
    """Repeated identical alerts should not flood the feed across check cycles."""
    payload = [_make_alert(agent_name="a1", alert_type="token")]
    first = await client.post("/api/v1/drift/alerts", json=payload)
    second = await client.post("/api/v1/drift/alerts", json=payload)
    assert first.json()["accepted"] == 1
    assert second.json()["accepted"] == 0  # deduped

    listed = await client.get("/api/v1/drift/alerts")
    assert len(listed.json()) == 1


@pytest.mark.asyncio
async def test_post_and_get_baseline_round_trip(client: AsyncClient) -> None:
    """A posted baseline must be retrievable with its full statistical payload."""
    resp = await client.post("/api/v1/drift/baselines", json=_make_baseline("a1"))
    assert resp.status_code == 200
    assert resp.json()["agent_name"] == "a1"

    got = await client.get("/api/v1/drift/baseline/a1")
    assert got.status_code == 200
    data = got.json()
    # The extended fields the detector needs to reload a baseline must be present.
    assert data["embedding_centroid"] == [0.1, 0.2, 0.3]
    assert data["response_length_distribution"] == [100.0, 140.0]
    assert data["tool_call_distribution"] == {"search": 0.7, "calc": 0.3}
    assert data["n_samples"] == 10


@pytest.mark.asyncio
async def test_rebuild_request_consume(client: AsyncClient) -> None:
    """A rebuild request can be consumed (deleted) by the detector."""
    await client.post("/api/v1/drift/baseline/a1/rebuild")
    pending = (await client.get("/api/v1/drift/rebuild-requests")).json()
    request_id = pending[0]["id"]

    consumed = await client.delete(f"/api/v1/drift/rebuild-requests/{request_id}")
    assert consumed.status_code == 200

    pending_after = await client.get("/api/v1/drift/rebuild-requests")
    assert pending_after.json() == []


@pytest.mark.asyncio
async def test_consume_unknown_rebuild_request_404(client: AsyncClient) -> None:
    resp = await client.delete("/api/v1/drift/rebuild-requests/9999")
    assert resp.status_code == 404
