"""Shared fixtures for drift detector tests."""

from __future__ import annotations

import numpy as np
import pytest

from detector.models import BaselineRecord, DriftConfig


@pytest.fixture
def drift_config() -> DriftConfig:
    """Default drift detection thresholds."""
    return DriftConfig()


@pytest.fixture
def sample_baseline() -> BaselineRecord:
    """A sample baseline for testing."""
    np.random.seed(42)
    centroid = np.random.randn(384).tolist()  # MiniLM-L6-v2 dimension

    return BaselineRecord(
        agent_name="test_agent",
        embedding_centroid=centroid,
        response_length_distribution=[100, 120, 110, 95, 130, 105, 115, 125, 108, 112],
        tool_call_distribution={"search": 0.6, "calculator": 0.3, "browser": 0.1},
        avg_response_length=112.0,
        avg_latency_ms=150.0,
        avg_token_count=200.0,
        n_samples=50,
    )
