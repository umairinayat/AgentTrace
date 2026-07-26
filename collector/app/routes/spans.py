"""Span ingestion endpoint."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Span, Trace
from app.schemas import BatchSpanRequest, BatchSpanResponse

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

    Auto-creates Trace records for new trace IDs.
    """
    if len(batch.spans) > MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"Batch too large: {len(batch.spans)} spans (max {MAX_BATCH_SIZE})",
        )

    accepted = 0

    for span_data in batch.spans:
        # Check if trace exists, create if not
        result = await session.execute(
            select(Trace).where(Trace.id == span_data.trace_id)
        )
        trace = result.scalar_one_or_none()

        if trace is None:
            trace = Trace(
                id=span_data.trace_id,
                name=span_data.agent_name,
                started_at=span_data.started_at,
                status="running",
            )
            session.add(trace)

        # Create span record
        span = Span(
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
        session.add(span)
        accepted += 1

        # Update trace aggregates
        if span_data.event_type in ("agent_end", "error"):
            trace.status = "error" if span_data.event_type == "error" else "completed"
            trace.ended_at = span_data.ended_at or datetime.now(UTC)
            if trace.started_at and trace.ended_at:
                delta = trace.ended_at - trace.started_at
                trace.duration_ms = delta.total_seconds() * 1000

        if span_data.total_tokens:
            trace.total_tokens = (trace.total_tokens or 0) + span_data.total_tokens
        if span_data.cost_usd:
            trace.total_cost_usd = (trace.total_cost_usd or 0) + span_data.cost_usd

    await session.flush()
    logger.info("Accepted %d spans", accepted)
    return BatchSpanResponse(accepted=accepted)
