"""Span ingestion endpoint."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Span, Trace
from app.schemas import BatchSpanRequest, BatchSpanResponse, SpanEventSchema
from app.timeutil import duration_ms

logger = logging.getLogger(__name__)

router = APIRouter(tags=["spans"])

# Upper bound on a single ingest batch to bound memory/CPU per request.
MAX_BATCH_SIZE = 1000


@router.post("/spans", response_model=BatchSpanResponse)
async def ingest_spans(
    batch: BatchSpanRequest,
    session: AsyncSession = Depends(get_session),
) -> BatchSpanResponse:
    """Ingest a batch of span events from the SDK.

    Ingestion is idempotent: delivery is at-least-once, so the SDK re-sends a
    batch whose response was lost. Spans whose ``span_id`` is already stored are
    counted as duplicates and skipped rather than raising an integrity error
    that would reject the whole batch. Trace aggregates are recomputed from the
    stored spans instead of incremented, so a replay cannot inflate them.
    """
    if len(batch.spans) > MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"Batch too large: {len(batch.spans)} spans (max {MAX_BATCH_SIZE})",
        )

    if not batch.spans:
        return BatchSpanResponse(accepted=0, duplicates=0)

    # De-duplicate within the batch itself, keeping the first occurrence.
    unique_spans: dict[str, SpanEventSchema] = {}
    for span_data in batch.spans:
        unique_spans.setdefault(span_data.span_id, span_data)

    # One query for span IDs we already hold, instead of one per span.
    existing_result = await session.execute(
        select(Span.id).where(Span.id.in_(list(unique_spans)))
    )
    existing_span_ids = set(existing_result.scalars().all())

    new_spans = [s for sid, s in unique_spans.items() if sid not in existing_span_ids]
    duplicates = len(batch.spans) - len(new_spans)

    if not new_spans:
        logger.info("Batch fully duplicate: %d spans skipped", duplicates)
        return BatchSpanResponse(accepted=0, duplicates=duplicates)

    trace_ids = {s.trace_id for s in new_spans}

    # One query for the traces this batch touches, instead of one per span.
    traces_result = await session.execute(select(Trace).where(Trace.id.in_(trace_ids)))
    traces = {t.id: t for t in traces_result.scalars().all()}

    for span_data in new_spans:
        trace = traces.get(span_data.trace_id)
        if trace is None:
            trace = Trace(
                id=span_data.trace_id,
                name=span_data.agent_name,
                started_at=span_data.started_at,
                status="running",
            )
            session.add(trace)
            traces[span_data.trace_id] = trace

        session.add(
            Span(
                id=span_data.span_id,
                trace_id=span_data.trace_id,
                parent_span_id=span_data.parent_span_id,
                agent_name=span_data.agent_name,
                event_type=span_data.event_type,
                started_at=span_data.started_at,
                ended_at=span_data.ended_at,
                latency_ms=span_data.latency_ms,
                model=span_data.model,
                prompt_tokens=span_data.prompt_tokens,
                completion_tokens=span_data.completion_tokens,
                total_tokens=span_data.total_tokens,
                cost_usd=span_data.cost_usd,
                input_data=span_data.input_data,
                output_data=span_data.output_data,
                error=span_data.error,
                metadata_=span_data.metadata,
            )
        )

        # Terminal events close the trace out.
        if span_data.event_type in ("agent_end", "error"):
            trace.status = "error" if span_data.event_type == "error" else "completed"
            trace.ended_at = span_data.ended_at or datetime.now(UTC)

    await session.flush()
    await _recompute_trace_totals(session, traces)

    accepted = len(new_spans)
    logger.info("Accepted %d spans (%d duplicates skipped)", accepted, duplicates)
    return BatchSpanResponse(accepted=accepted, duplicates=duplicates)


async def _recompute_trace_totals(
    session: AsyncSession, traces: dict[str, Trace]
) -> None:
    """Recompute token/cost/duration totals for the given traces from their spans.

    Derived from stored rows rather than accumulated per request, so replayed or
    out-of-order batches converge on the same answer instead of double-counting.
    """
    totals_result = await session.execute(
        select(
            Span.trace_id,
            func.coalesce(func.sum(Span.total_tokens), 0),
            func.coalesce(func.sum(Span.cost_usd), 0.0),
        )
        .where(Span.trace_id.in_(list(traces)))
        .group_by(Span.trace_id)
    )

    for trace_id, total_tokens, total_cost in totals_result.all():
        trace = traces[trace_id]
        trace.total_tokens = int(total_tokens) or None
        trace.total_cost_usd = float(total_cost) or None
        if trace.started_at and trace.ended_at:
            trace.duration_ms = duration_ms(trace.started_at, trace.ended_at)
