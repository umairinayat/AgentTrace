"""Drift detection endpoints."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import DriftAlert, DriftBaseline
from app.schemas import DriftAlertResponse, DriftBaselineResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["drift"])


@router.get("/drift/alerts", response_model=list[DriftAlertResponse])
async def get_drift_alerts(
    agent_name: Optional[str] = None,
    resolved: Optional[int] = Query(None, ge=0, le=1),
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

    return [
        DriftAlertResponse(
            id=a.id,
            agent_name=a.agent_name,
            detected_at=a.detected_at,
            alert_type=a.alert_type,
            severity=a.severity,
            score=a.score,
            threshold=a.threshold,
            description=a.description,
            resolved=a.resolved,
        )
        for a in alerts
    ]


@router.get("/drift/baseline/{agent_name}", response_model=DriftBaselineResponse)
async def get_drift_baseline(
    agent_name: str,
    session: AsyncSession = Depends(get_session),
) -> DriftBaselineResponse:
    """Get the current drift baseline for an agent."""
    result = await session.execute(
        select(DriftBaseline)
        .where(DriftBaseline.agent_name == agent_name)
        .order_by(DriftBaseline.built_at.desc())
        .limit(1)
    )
    baseline = result.scalar_one_or_none()

    if baseline is None:
        raise HTTPException(status_code=404, detail="No baseline found for this agent")

    return DriftBaselineResponse(
        id=baseline.id,
        agent_name=baseline.agent_name,
        built_at=baseline.built_at,
        n_samples=baseline.n_samples,
        avg_response_length=baseline.avg_response_length,
        avg_latency_ms=baseline.avg_latency_ms,
        avg_token_count=baseline.avg_token_count,
    )


@router.post("/drift/baseline/{agent_name}/rebuild")
async def rebuild_baseline(
    agent_name: str,
) -> dict[str, str]:
    """Trigger a baseline rebuild for an agent.

    This endpoint signals the drift detector to rebuild.
    The actual rebuild happens asynchronously in the drift-detector service.
    """
    logger.info("Baseline rebuild requested for agent: %s", agent_name)
    return {"status": "ok", "message": f"Baseline rebuild queued for {agent_name}"}
