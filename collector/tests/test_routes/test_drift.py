"""Tests for the drift endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


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
    """Rebuild endpoint should return ok."""
    resp = await client.post("/api/v1/drift/baseline/test_agent/rebuild")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
