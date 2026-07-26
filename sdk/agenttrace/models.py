"""Pydantic v2 models for AgentTrace trace events."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

from agenttrace._version import SDK_VERSION


def _utcnow() -> datetime:
    """Return timezone-aware UTC now."""
    return datetime.now(UTC)


def _uuid() -> str:
    """Generate a new UUID4 string."""
    return str(uuid.uuid4())


class SpanEvent(BaseModel):
    """A single unit of trace data -- one LLM call, tool call, or agent lifecycle event."""

    # Identity
    trace_id: str = Field(default_factory=_uuid)
    span_id: str = Field(default_factory=_uuid)
    parent_span_id: str | None = None

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
    ended_at: datetime | None = None
    latency_ms: float | None = None

    # LLM-specific
    model: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    cost_usd: float | None = None

    # Payload
    input_data: dict[str, object] | None = None
    output_data: dict[str, object] | None = None

    # Extra
    error: str | None = None
    metadata: dict[str, object] | None = None
    sdk_version: str = Field(default=SDK_VERSION)


class BatchSpanRequest(BaseModel):
    """What the SDK sends to the Collector -- a batch of spans."""

    spans: list[SpanEvent]
    agent_session_id: str | None = None


class TraceContext(BaseModel):
    """Stored in contextvars for async propagation."""

    trace_id: str
    parent_span_id: str | None = None
    agent_name: str
