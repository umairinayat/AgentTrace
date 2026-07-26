"""Data models for drift detection."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class DriftConfig(BaseModel):
    """Configuration for drift detection thresholds."""

    semantic_threshold: float = 0.15
    ks_pvalue_threshold: float = 0.05
    token_change_threshold: float = 0.20
    tool_change_threshold: float = 0.20
    latency_change_threshold: float = 0.50
    min_samples: int = 10


class BaselineRecord(BaseModel):
    """Stored baseline for an agent."""

    agent_name: str
    built_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    n_samples: int
    avg_response_length: float
    avg_latency_ms: float
    avg_token_count: float
    embedding_centroid: list[float]
    response_length_distribution: list[float]
    tool_call_distribution: dict[str, float]


class DriftAlert(BaseModel):
    """A detected drift alert."""

    agent_name: str
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    alert_type: str  # semantic | distribution | token | tool
    severity: str = "warning"  # warning | critical
    score: float
    threshold: float
    description: str


class DriftReport(BaseModel):
    """Results of a drift comparison."""

    agent_name: str
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    alerts: list[DriftAlert]
    is_drifted: bool
    cosine_distance: Optional[float] = None
    ks_p_value: Optional[float] = None
    token_pct_change: Optional[float] = None
