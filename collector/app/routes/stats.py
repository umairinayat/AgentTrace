"""Aggregated statistics endpoint."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Span, Trace
from app.schemas import StatsResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["stats"])


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    session: AsyncSession = Depends(get_session),
) -> StatsResponse:
    """Get aggregated statistics across all traces."""
    # Total traces
    trace_count = await session.execute(select(func.count(Trace.id)))
    total_traces = trace_count.scalar() or 0

    # Total spans
    span_count = await session.execute(select(func.count(Span.id)))
    total_spans = span_count.scalar() or 0

    # Total tokens
    token_sum = await session.execute(select(func.coalesce(func.sum(Span.total_tokens), 0)))
    total_tokens = token_sum.scalar() or 0

    # Total cost
    cost_sum = await session.execute(select(func.coalesce(func.sum(Span.cost_usd), 0.0)))
    total_cost = cost_sum.scalar() or 0.0

    # Average latency
    avg_lat = await session.execute(select(func.coalesce(func.avg(Span.latency_ms), 0.0)))
    avg_latency = avg_lat.scalar() or 0.0

    # Avg cost per trace
    avg_cost = total_cost / total_traces if total_traces > 0 else 0.0

    # Traces by status
    status_query = await session.execute(
        select(Trace.status, func.count(Trace.id)).group_by(Trace.status)
    )
    traces_by_status = {row[0]: row[1] for row in status_query.all()}

    # Top agents by cost
    agent_query = await session.execute(
        select(
            Span.agent_name,
            func.sum(Span.cost_usd).label("total_cost"),
            func.count(Span.id).label("span_count"),
        )
        .group_by(Span.agent_name)
        .order_by(func.sum(Span.cost_usd).desc())
        .limit(10)
    )
    top_agents = [
        {"name": row[0], "total_cost": row[1] or 0, "span_count": row[2]}
        for row in agent_query.all()
    ]

    # Top models by usage
    model_query = await session.execute(
        select(
            Span.model,
            func.sum(Span.total_tokens).label("total_tokens"),
            func.sum(Span.cost_usd).label("total_cost"),
            func.count(Span.id).label("call_count"),
        )
        .where(Span.model.isnot(None))
        .group_by(Span.model)
        .order_by(func.sum(Span.total_tokens).desc())
        .limit(10)
    )
    top_models = [
        {
            "name": row[0],
            "total_tokens": row[1] or 0,
            "total_cost": row[2] or 0,
            "call_count": row[3],
        }
        for row in model_query.all()
    ]

    return StatsResponse(
        total_traces=total_traces,
        total_spans=total_spans,
        total_tokens=total_tokens,
        total_cost_usd=round(total_cost, 6),
        avg_latency_ms=round(avg_latency, 2),
        avg_cost_per_trace=round(avg_cost, 6),
        traces_by_status=traces_by_status,
        top_agents=top_agents,
        top_models=top_models,
    )
