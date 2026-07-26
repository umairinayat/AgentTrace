"""Pydantic request/response schemas for the Collector API."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# --- Request schemas ---


class SpanEventSchema(BaseModel):
    """Incoming span event from the SDK."""

    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    agent_name: str
    event_type: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    latency_ms: Optional[float] = None
    model: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    cost_usd: Optional[float] = None
    input_data: Optional[dict[str, object]] = None
    output_data: Optional[dict[str, object]] = None
    error: Optional[str] = None
    metadata: Optional[dict[str, object]] = None
    sdk_version: str = "0.1.0"


class BatchSpanRequest(BaseModel):
    """Batch of spans from the SDK."""

    spans: list[SpanEventSchema]
    agent_session_id: Optional[str] = None


# --- Response schemas ---


class BatchSpanResponse(BaseModel):
    """Response to batch span ingestion."""

    accepted: int


class SpanResponse(BaseModel):
    """Span data in API responses."""

    id: str
    trace_id: str
    parent_span_id: Optional[str] = None
    agent_name: str
    event_type: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    latency_ms: Optional[float] = None
    model: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    cost_usd: Optional[float] = None
    input_data: Optional[dict[str, object]] = None
    output_data: Optional[dict[str, object]] = None
    error: Optional[str] = None
    metadata: Optional[dict[str, object]] = None

    model_config = {"from_attributes": True}


class TraceResponse(BaseModel):
    """Trace summary for list view."""

    id: str
    name: str
    agent_name: Optional[str] = None
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_ms: Optional[float] = None
    total_tokens: Optional[int] = None
    total_cost_usd: Optional[float] = None
    status: str
    span_count: int = 0

    model_config = {"from_attributes": True}


class TraceDetailResponse(BaseModel):
    """Full trace with all spans."""

    id: str
    name: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_ms: Optional[float] = None
    total_tokens: Optional[int] = None
    total_cost_usd: Optional[float] = None
    status: str
    metadata: Optional[dict[str, object]] = None
    spans: list[SpanResponse]

    model_config = {"from_attributes": True}


class TimelineSpan(BaseModel):
    """Span formatted for Gantt timeline visualization."""

    span_id: str
    parent_span_id: Optional[str] = None
    agent_name: str
    event_type: str
    start_offset_ms: float
    duration_ms: float
    model: Optional[str] = None
    total_tokens: Optional[int] = None
    cost_usd: Optional[float] = None
    error: Optional[str] = None


class TimelineData(BaseModel):
    """Gantt timeline data for a trace."""

    trace_id: str
    trace_start: datetime
    total_duration_ms: float
    spans: list[TimelineSpan]


class StatsResponse(BaseModel):
    """Aggregated statistics."""

    total_traces: int
    total_spans: int
    total_tokens: int
    total_cost_usd: float
    avg_latency_ms: float
    avg_cost_per_trace: float
    traces_by_status: dict[str, int]
    top_agents: list[dict[str, object]]
    top_models: list[dict[str, object]]


class DriftAlertResponse(BaseModel):
    """Drift alert in API responses."""

    id: int
    agent_name: str
    detected_at: datetime
    alert_type: str
    severity: str
    score: Optional[float] = None
    threshold: Optional[float] = None
    description: Optional[str] = None
    resolved: int = 0

    model_config = {"from_attributes": True}


class DriftBaselineResponse(BaseModel):
    """Drift baseline in API responses.

    Includes the full statistical payload (embedding centroid and distributions)
    so the drift detector can reload a baseline after a restart without rebuilding.
    """

    id: int
    agent_name: str
    built_at: datetime
    n_samples: int
    avg_response_length: Optional[float] = None
    avg_latency_ms: Optional[float] = None
    avg_token_count: Optional[float] = None
    embedding_centroid: Optional[list[float]] = None
    response_length_distribution: Optional[list[float]] = None
    tool_call_distribution: Optional[dict[str, float]] = None

    model_config = {"from_attributes": True}


class DriftBaselineCreate(BaseModel):
    """Payload the drift detector sends when persisting a freshly built baseline."""

    agent_name: str
    n_samples: int
    avg_response_length: Optional[float] = None
    avg_latency_ms: Optional[float] = None
    avg_token_count: Optional[float] = None
    embedding_centroid: Optional[list[float]] = None
    response_length_distribution: Optional[list[float]] = None
    tool_call_distribution: Optional[dict[str, float]] = None


class DriftAlertCreate(BaseModel):
    """Payload the drift detector sends when posting a detected alert."""

    agent_name: str
    detected_at: Optional[datetime] = None
    alert_type: str
    severity: str = "warning"
    score: Optional[float] = None
    threshold: Optional[float] = None
    description: Optional[str] = None


class DriftRebuildRequestResponse(BaseModel):
    """A pending baseline rebuild request."""

    id: int
    agent_name: str
    requested_at: datetime

    model_config = {"from_attributes": True}


class AgentSummary(BaseModel):
    """An agent observed in stored spans."""

    name: str
    span_count: int


class PaginatedTraces(BaseModel):
    """Paginated trace list response."""

    items: list[TraceResponse]
    total: int
    page: int
    page_size: int
    pages: int


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "ok"
