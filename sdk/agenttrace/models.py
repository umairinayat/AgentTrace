"""Pydantic v2 models for AgentTrace trace events."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field

from agenttrace._version import SDK_VERSION


def _utcnow() -> datetime:
    """Return timezone-aware UTC now."""
    return datetime.now(timezone.utc)


def _uuid() -> str:
    """Generate a new UUID4 string."""
    return str(uuid.uuid4())


class SpanEvent(BaseModel):
    """A single unit of trace data -- one LLM call, tool call, or agent lifecycle event."""

    # Identity
    trace_id: str = Field(default_factory=_uuid)
    span_id: str = Field(default_factory=_uuid)
    parent_span_id: Optional[str] = None

    # Classification
    agent_name: str
    event_type: Literal[
        "agent_start",
        "agent_end",
        "llm_call",
        "tool_call",
        "tool_end",
        "message",
        "error",
    ]

    # Timing
    started_at: datetime = Field(default_factory=_utcnow)
    ended_at: Optional[datetime] = None
    latency_ms: Optional[float] = None

    # LLM-specific
    model: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    cost_usd: Optional[float] = None

    # Payload
    input_data: Optional[dict[str, object]] = None
    output_data: Optional[dict[str, object]] = None

    # Extra
    error: Optional[str] = None
    metadata: Optional[dict[str, object]] = None
    sdk_version: str = Field(default=SDK_VERSION)


class BatchSpanRequest(BaseModel):
    """What the SDK sends to the Collector -- a batch of spans."""

    spans: list[SpanEvent]
    agent_session_id: Optional[str] = None


class TraceContext(BaseModel):
    """Stored in contextvars for async propagation."""

    trace_id: str
    parent_span_id: Optional[str] = None
    agent_name: str
