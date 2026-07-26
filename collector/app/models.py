"""SQLAlchemy async ORM models for trace storage."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


class Trace(Base):
    """A complete agent execution trace containing multiple spans."""

    __tablename__ = "traces"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    started_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    ended_at = Column(DateTime, nullable=True)
    duration_ms = Column(Float, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    total_cost_usd = Column(Float, nullable=True)
    status = Column(String, default="running")
    metadata_ = Column("metadata", JSON, nullable=True)

    spans = relationship("Span", back_populates="trace", cascade="all, delete-orphan")


class Span(Base):
    """A single span within a trace -- one LLM call, tool call, or agent event."""

    __tablename__ = "spans"

    id = Column(String, primary_key=True)
    trace_id = Column(String, ForeignKey("traces.id"), nullable=False, index=True)
    parent_span_id = Column(String, nullable=True)
    agent_name = Column(String, nullable=False, index=True)
    event_type = Column(String, nullable=False)
    started_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime, nullable=True)
    latency_ms = Column(Float, nullable=True)
    model = Column(String, nullable=True)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    cost_usd = Column(Float, nullable=True)
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    metadata_ = Column("metadata", JSON, nullable=True)

    trace = relationship("Trace", back_populates="spans")


class DriftBaseline(Base):
    """Statistical baseline for behavioral drift detection."""

    __tablename__ = "drift_baselines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_name = Column(String, nullable=False, index=True)
    built_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    n_samples = Column(Integer, nullable=False)
    avg_response_length = Column(Float, nullable=True)
    avg_latency_ms = Column(Float, nullable=True)
    avg_token_count = Column(Float, nullable=True)
    embedding_centroid = Column(JSON, nullable=True)
    response_length_distribution = Column(JSON, nullable=True)
    tool_call_distribution = Column(JSON, nullable=True)


class DriftAlert(Base):
    """A detected behavioral drift alert."""

    __tablename__ = "drift_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_name = Column(String, nullable=False, index=True)
    detected_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    alert_type = Column(String, nullable=False)
    severity = Column(String, default="warning")
    score = Column(Float, nullable=True)
    threshold = Column(Float, nullable=True)
    description = Column(Text, nullable=True)
    resolved = Column(Integer, default=0)


class DriftRebuildRequest(Base):
    """A pending baseline rebuild request, consumed by the drift detector."""

    __tablename__ = "drift_rebuild_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_name = Column(String, nullable=False, index=True)
    requested_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
