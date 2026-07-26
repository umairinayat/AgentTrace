"""Agent enumeration endpoint.

Returns every agent name observed in stored spans (uncapped), used by the drift
detector to decide which agents to check. The ``/stats`` endpoint only exposes a
top-10-by-cost view, which would silently skip drift for any agent outside it.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Span
from app.schemas import AgentSummary

router = APIRouter(tags=["agents"])


@router.get("/agents", response_model=list[AgentSummary])
async def list_agents(
    session: AsyncSession = Depends(get_session),
) -> list[AgentSummary]:
    """List all distinct agent names with their span counts."""
    result = await session.execute(
        select(Span.agent_name, func.count(Span.id))
        .group_by(Span.agent_name)
        .order_by(func.count(Span.id).desc())
    )
    return [
        AgentSummary(name=name, span_count=count) for name, count in result.all()
    ]
