"""Drift detection endpoints.

These endpoints are the persistence surface for the drift detector worker:

* ``POST /drift/alerts``           -- the detector posts detected alerts here.
* ``GET  /drift/alerts``           -- the dashboard reads alerts to display.
* ``POST /drift/baselines``        -- the detector persists a freshly built baseline.
* ``GET  /drift/baseline/{agent}`` -- the detector loads a baseline to compare against.
* ``POST /drift/baseline/{agent}/rebuild`` -- the dashboard requests a rebuild.
* ``GET  /drift/rebuild-requests`` -- the detector polls pending rebuild requests.
* ``DELETE /drift/rebuild-requests/{id}`` -- the detector consumes a request.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import DriftAlert, DriftBaseline, DriftRebuildRequest
from app.schemas import (
    DriftAlertCreate,
    DriftAlertResponse,
    DriftBaselineCreate,
    DriftBaselineResponse,
    DriftRebuildRequestResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["drift"])


@router.get("/drift/alerts", response_model=list[DriftAlertResponse])
async def get_drift_alerts(
    agent_name: str | None = None,
    resolved: int | None = Query(None, ge=0, le=1),
    session: AsyncSession = Depends(get_session),
) -> list[DriftAlertResponse]:
    """Get drift alerts, optionally filtered by agent and resolution status."""
    query = select(DriftAlert).order_by(DriftAlert.detected_at.desc())

    if agent_name:
        query = query.where(DriftAlert.agent_name == agent_name)
    if resolved is not None:
        query = query.where(DriftAlert.resolved == resolved)

    result = await session.execute(query)
    alerts = result.scalars().all()

    return [DriftAlertResponse.model_validate(a) for a in alerts]


@router.post("/drift/alerts")
async def post_drift_alerts(
    alerts: list[DriftAlertCreate],
    session: AsyncSession = Depends(get_session),
) -> dict[str, int]:
    """Ingest drift alerts posted by the drift detector.

    Deduplicates against the most recent identical unresolved alert per agent to
    avoid flooding the feed on every check cycle.
    """
    accepted = 0
    now = datetime.now(UTC)

    for payload in alerts:
        detected_at = payload.detected_at or now

        # Skip if an identical unresolved alert already exists for this agent/type.
        existing = await session.execute(
            select(DriftAlert).where(
                DriftAlert.agent_name == payload.agent_name,
                DriftAlert.alert_type == payload.alert_type,
                DriftAlert.resolved == 0,
            )
        )
        if existing.scalars().first() is not None:
            continue

        session.add(
            DriftAlert(
                agent_name=payload.agent_name,
                detected_at=detected_at,
                alert_type=payload.alert_type,
                severity=payload.severity,
                score=payload.score,
                threshold=payload.threshold,
                description=payload.description,
                resolved=0,
            )
        )
        accepted += 1

    logger.info("Accepted %d drift alerts", accepted)
    return {"accepted": accepted}


@router.get("/drift/baseline/{agent_name}", response_model=DriftBaselineResponse)
async def get_drift_baseline(
    agent_name: str,
    session: AsyncSession = Depends(get_session),
) -> DriftBaselineResponse:
    """Get the most recent drift baseline for an agent."""
    result = await session.execute(
        select(DriftBaseline)
        .where(DriftBaseline.agent_name == agent_name)
        .order_by(DriftBaseline.built_at.desc())
        .limit(1)
    )
    baseline = result.scalar_one_or_none()

    if baseline is None:
        raise HTTPException(status_code=404, detail="No baseline found for this agent")

    return DriftBaselineResponse.model_validate(baseline)


@router.post("/drift/baselines", response_model=DriftBaselineResponse)
async def post_drift_baseline(
    payload: DriftBaselineCreate,
    session: AsyncSession = Depends(get_session),
) -> DriftBaselineResponse:
    """Persist a freshly built baseline from the drift detector.

    Baselines are append-only (history is retained) so drift can be analyzed
    over time; consumers always read the most recent via GET.
    """
    baseline = DriftBaseline(
        agent_name=payload.agent_name,
        n_samples=payload.n_samples,
        avg_response_length=payload.avg_response_length,
        avg_latency_ms=payload.avg_latency_ms,
        avg_token_count=payload.avg_token_count,
        embedding_centroid=payload.embedding_centroid,
        response_length_distribution=payload.response_length_distribution,
        tool_call_distribution=payload.tool_call_distribution,
    )
    session.add(baseline)
    await session.flush()
    return DriftBaselineResponse.model_validate(baseline)


@router.post("/drift/baseline/{agent_name}/rebuild")
async def rebuild_baseline(
    agent_name: str,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    """Queue a baseline rebuild for an agent.

    Inserts a rebuild request row that the drift detector polls and consumes on
    its next check cycle.
    """
    request = DriftRebuildRequest(agent_name=agent_name)
    session.add(request)
    logger.info("Baseline rebuild queued for agent: %s", agent_name)
    return {"status": "ok", "message": f"Baseline rebuild queued for {agent_name}"}


@router.get("/drift/rebuild-requests", response_model=list[DriftRebuildRequestResponse])
async def list_rebuild_requests(
    agent_name: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[DriftRebuildRequestResponse]:
    """List pending (unconsumed) baseline rebuild requests."""
    query = select(DriftRebuildRequest).order_by(DriftRebuildRequest.requested_at.asc())
    if agent_name:
        query = query.where(DriftRebuildRequest.agent_name == agent_name)
    result = await session.execute(query)
    return [DriftRebuildRequestResponse.model_validate(r) for r in result.scalars().all()]


@router.delete("/drift/rebuild-requests/{request_id}")
async def consume_rebuild_request(
    request_id: int,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    """Mark a rebuild request as consumed (the detector rebuilt that baseline)."""
    result = await session.execute(
        select(DriftRebuildRequest).where(DriftRebuildRequest.id == request_id)
    )
    request = result.scalar_one_or_none()
    if request is None:
        raise HTTPException(status_code=404, detail="Rebuild request not found")
    await session.delete(request)
    return {"status": "ok"}
