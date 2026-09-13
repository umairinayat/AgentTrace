"""Trace listing and detail endpoints."""

from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.models import Span, Trace
from app.schemas import (
    PaginatedTraces,
    SpanResponse,
    TimelineData,
    TimelineSpan,
    TraceDetailResponse,
    TraceResponse,
)
from app.timeutil import duration_ms

logger = logging.getLogger(__name__)

router = APIRouter(tags=["traces"])


@router.get("/traces", response_model=PaginatedTraces)
async def list_traces(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    agent_name: str | None = None,
    status: str | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    min_cost: float | None = None,
    sort_by: str = Query("started_at", pattern="^(started_at|cost|duration|tokens)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    session: AsyncSession = Depends(get_session),
) -> PaginatedTraces:
    """List all traces with pagination and filters."""
    query = select(Trace)

    # Apply filters
    if agent_name:
        # Filter by the indexed Span.agent_name rather than Trace.name, which is
        # only incidentally set to an agent name at ingest time.
        trace_ids_for_agent = select(Span.trace_id).where(Span.agent_name == agent_name)
        query = query.where(Trace.id.in_(trace_ids_for_agent))
    if status:
        query = query.where(Trace.status == status)
    if from_date:
        query = query.where(Trace.started_at >= from_date)
    if to_date:
        query = query.where(Trace.started_at <= to_date)
    if min_cost is not None:
        query = query.where(Trace.total_cost_usd >= min_cost)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    # Sorting
    sort_column_map = {
        "started_at": Trace.started_at,
        "cost": Trace.total_cost_usd,
        "duration": Trace.duration_ms,
        "tokens": Trace.total_tokens,
    }
    sort_col = sort_column_map.get(sort_by, Trace.started_at)
    if sort_order == "desc":
        query = query.order_by(sort_col.desc())
    else:
        query = query.order_by(sort_col.asc())

    # Pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # Span count and the owning agent come from correlated aggregates rather
    # than eager-loading Trace.spans: the list view needs two scalars per trace,
    # and selectinload would pull every span's full input/output JSON to get them.
    span_count_sq = (
        select(func.count(Span.id))
        .where(Span.trace_id == Trace.id)
        .correlate(Trace)
        .scalar_subquery()
    )
    first_agent_sq = (
        select(Span.agent_name)
        .where(Span.trace_id == Trace.id)
        .order_by(Span.started_at.asc())
        .limit(1)
        .correlate(Trace)
        .scalar_subquery()
    )

    result = await session.execute(
        query.add_columns(
            span_count_sq.label("span_count"),
            first_agent_sq.label("first_agent"),
        )
    )

    items = [
        TraceResponse(
            id=trace.id,
            name=trace.name,
            agent_name=first_agent,
            started_at=trace.started_at,
            ended_at=trace.ended_at,
            duration_ms=trace.duration_ms,
            total_tokens=trace.total_tokens,
            total_cost_usd=trace.total_cost_usd,
            status=trace.status,
            span_count=span_count,
        )
        for trace, span_count, first_agent in result.all()
    ]

    pages = max(1, (total + page_size - 1) // page_size)
    return PaginatedTraces(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/traces/{trace_id}", response_model=TraceDetailResponse)
async def get_trace(
    trace_id: str,
    session: AsyncSession = Depends(get_session),
) -> TraceDetailResponse:
    """Get full trace with all spans."""
    result = await session.execute(
        select(Trace)
        .where(Trace.id == trace_id)
        .options(selectinload(Trace.spans))
    )
    trace = result.scalar_one_or_none()

    if trace is None:
        raise HTTPException(status_code=404, detail="Trace not found")

    spans = [
        SpanResponse(
            id=s.id,
            trace_id=s.trace_id,
            parent_span_id=s.parent_span_id,
            agent_name=s.agent_name,
            event_type=s.event_type,
            started_at=s.started_at,
            ended_at=s.ended_at,
            latency_ms=s.latency_ms,
            model=s.model,
            prompt_tokens=s.prompt_tokens,
            completion_tokens=s.completion_tokens,
            total_tokens=s.total_tokens,
            cost_usd=s.cost_usd,
            input_data=s.input_data,
            output_data=s.output_data,
            error=s.error,
            metadata=s.metadata_,
        )
        for s in trace.spans
    ]

    return TraceDetailResponse(
        id=trace.id,
        name=trace.name,
        started_at=trace.started_at,
        ended_at=trace.ended_at,
        duration_ms=trace.duration_ms,
        total_tokens=trace.total_tokens,
        total_cost_usd=trace.total_cost_usd,
        status=trace.status,
        metadata=trace.metadata_,
        spans=spans,
    )


@router.get("/traces/{trace_id}/timeline", response_model=TimelineData)
async def get_trace_timeline(
    trace_id: str,
    session: AsyncSession = Depends(get_session),
) -> TimelineData:
    """Get Gantt-format timeline data for a trace."""
    result = await session.execute(
        select(Trace)
        .where(Trace.id == trace_id)
        .options(selectinload(Trace.spans))
    )
    trace = result.scalar_one_or_none()

    if trace is None:
        raise HTTPException(status_code=404, detail="Trace not found")

    trace_start = trace.started_at
    timeline_spans = []

    for s in trace.spans:
        start_offset = duration_ms(trace_start, s.started_at)
        duration = s.latency_ms or 0

        timeline_spans.append(
            TimelineSpan(
                span_id=s.id,
                parent_span_id=s.parent_span_id,
                agent_name=s.agent_name,
                event_type=s.event_type,
                start_offset_ms=start_offset,
                duration_ms=duration,
                model=s.model,
                total_tokens=s.total_tokens,
                cost_usd=s.cost_usd,
                error=s.error,
            )
        )

    return TimelineData(
        trace_id=trace.id,
        trace_start=trace_start,
        total_duration_ms=trace.duration_ms or 0,
        spans=timeline_spans,
    )
