"""Tests for drift comparator with mock baselines and intentionally drifted data."""

from __future__ import annotations

import pytest

from detector.comparator import DriftComparator
from detector.models import BaselineRecord, DriftConfig


@pytest.fixture
def baseline() -> BaselineRecord:
    """Create a mock baseline with known values."""
    return BaselineRecord(
        agent_name="test_agent",
        n_samples=50,
        avg_response_length=200.0,
        avg_latency_ms=150.0,
        avg_token_count=100.0,
        embedding_centroid=[0.1] * 384,  # MiniLM-L6-v2 dim
        response_length_distribution=[200.0] * 50,
        tool_call_distribution={"search": 0.6, "calculate": 0.4},
    )


@pytest.fixture
def config() -> DriftConfig:
    """Create default drift config."""
    return DriftConfig()


class TestDriftComparator:
    """Tests for drift detection logic."""

    def test_no_drift_similar_data(self, baseline: BaselineRecord, config: DriftConfig) -> None:
        """No alerts when data is similar to baseline."""
        comparator = DriftComparator.__new__(DriftComparator)
        comparator._model_name = "all-MiniLM-L6-v2"
        comparator._embedder = None

        # Skip semantic check by not providing texts
        report = comparator.compare(
            baseline=baseline,
            recent_texts=[],
            recent_latencies=[150.0] * 10,
            recent_token_counts=[100] * 10,
            recent_tool_calls=["search"] * 6 + ["calculate"] * 4,
            config=config,
        )

        assert not report.is_drifted
        assert len(report.alerts) == 0

    def test_token_drift_detected(self, baseline: BaselineRecord, config: DriftConfig) -> None:
        """Should detect token count anomaly."""
        comparator = DriftComparator.__new__(DriftComparator)
        comparator._model_name = "all-MiniLM-L6-v2"
        comparator._embedder = None

        # 50% more tokens than baseline (threshold is 20%)
        report = comparator.compare(
            baseline=baseline,
            recent_texts=[],
            recent_latencies=[150.0] * 10,
            recent_token_counts=[150] * 10,  # 50% increase
            recent_tool_calls=[],
            config=config,
        )

        assert report.is_drifted
        token_alerts = [a for a in report.alerts if a.alert_type == "token"]
        assert len(token_alerts) == 1
        assert token_alerts[0].score == pytest.approx(0.5, abs=0.01)

    def test_distribution_drift_detected(
        self, baseline: BaselineRecord, config: DriftConfig
    ) -> None:
        """Should detect response length distribution shift."""
        comparator = DriftComparator.__new__(DriftComparator)
        comparator._model_name = "all-MiniLM-L6-v2"
        comparator._embedder = None

        # Dramatically different response lengths
        report = comparator.compare(
            baseline=baseline,
            recent_texts=["x" * 1000] * 20,  # Much longer responses
            recent_latencies=[],
            recent_token_counts=[],
            recent_tool_calls=[],
            config=config,
        )

        dist_alerts = [a for a in report.alerts if a.alert_type == "distribution"]
        assert len(dist_alerts) == 1

    def test_tool_pattern_drift(self, baseline: BaselineRecord, config: DriftConfig) -> None:
        """Should detect tool call pattern changes."""
        comparator = DriftComparator.__new__(DriftComparator)
        comparator._model_name = "all-MiniLM-L6-v2"
        comparator._embedder = None

        # Completely different tool usage pattern
        report = comparator.compare(
            baseline=baseline,
            recent_texts=[],
            recent_latencies=[],
            recent_token_counts=[],
            recent_tool_calls=["new_tool"] * 10,  # New tool, not in baseline
            config=config,
        )

        tool_alerts = [a for a in report.alerts if a.alert_type == "tool"]
        assert len(tool_alerts) == 1

    def test_no_drift_within_thresholds(
        self, baseline: BaselineRecord, config: DriftConfig
    ) -> None:
        """Should not alert when changes are within thresholds."""
        comparator = DriftComparator.__new__(DriftComparator)
        comparator._model_name = "all-MiniLM-L6-v2"
        comparator._embedder = None

        # 10% token change (below 20% threshold)
        report = comparator.compare(
            baseline=baseline,
            recent_texts=[],
            recent_latencies=[],
            recent_token_counts=[110] * 10,  # 10% increase
            recent_tool_calls=["search"] * 6 + ["calculate"] * 4,
            config=config,
        )

        assert not report.is_drifted
