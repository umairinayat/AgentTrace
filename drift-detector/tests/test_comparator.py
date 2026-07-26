"""Tests for drift comparator with controlled baselines and drifted data."""

from __future__ import annotations

import pytest

from detector.baseline import BaselineBuilder
from detector.comparator import DriftComparator
from detector.models import BaselineRecord, DriftConfig


@pytest.fixture
def baseline() -> BaselineRecord:
    """Create a baseline with known values (used by numeric-only checks)."""
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
        comparator = DriftComparator()  # no texts -> embedder never loaded

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
        comparator = DriftComparator()

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

    def test_latency_drift_detected(self, baseline: BaselineRecord, config: DriftConfig) -> None:
        """Should detect latency anomaly (recent_latencies was previously unused)."""
        comparator = DriftComparator()

        report = comparator.compare(
            baseline=baseline,
            recent_texts=[],
            recent_latencies=[1000.0] * 10,  # baseline 150ms -> ~567% change
            recent_token_counts=[],
            recent_tool_calls=[],
            config=config,
        )

        latency_alerts = [a for a in report.alerts if a.alert_type == "latency"]
        assert len(latency_alerts) == 1
        assert latency_alerts[0].score > config.latency_change_threshold

    def test_distribution_drift_detected(
        self, fake_embedder, config: DriftConfig
    ) -> None:
        """Should detect response length distribution shift (semantic kept quiet)."""
        # All texts map to the same vector so the semantic check stays silent,
        # isolating the distribution check to the response lengths.
        fake_embedder.set("baseline text", [1.0, 0.0, 0.0, 0.0])
        fake_embedder.set("x" * 1000, [1.0, 0.0, 0.0, 0.0])

        builder = BaselineBuilder(embedder=fake_embedder)
        baseline = builder.build(
            "test_agent", ["baseline text"] * 10, [100.0] * 10, [50] * 10, []
        )

        comparator = DriftComparator(embedder=fake_embedder)
        report = comparator.compare(
            baseline=baseline,
            recent_texts=["x" * 1000] * 10,
            recent_latencies=[],
            recent_token_counts=[],
            recent_tool_calls=[],
            config=config,
        )

        dist_alerts = [a for a in report.alerts if a.alert_type == "distribution"]
        assert len(dist_alerts) == 1

    def test_semantic_drift_detected(self, fake_embedder, config: DriftConfig) -> None:
        """Should detect semantic drift via embedding cosine distance."""
        # Orthogonal centroids -> cosine distance 1.0, well above threshold.
        fake_embedder.set("baseline response", [1.0, 0.0, 0.0, 0.0])
        fake_embedder.set("drifted response", [0.0, 1.0, 0.0, 0.0])

        builder = BaselineBuilder(embedder=fake_embedder)
        baseline = builder.build(
            "test_agent", ["baseline response"] * 5, [100.0] * 5, [50] * 5, []
        )

        comparator = DriftComparator(embedder=fake_embedder)
        report = comparator.compare(
            baseline=baseline,
            recent_texts=["drifted response"] * 5,
            recent_latencies=[],
            recent_token_counts=[],
            recent_tool_calls=[],
            config=config,
        )

        semantic_alerts = [a for a in report.alerts if a.alert_type == "semantic"]
        assert len(semantic_alerts) == 1
        assert semantic_alerts[0].score == pytest.approx(1.0, abs=0.01)

    def test_tool_pattern_drift(self, baseline: BaselineRecord, config: DriftConfig) -> None:
        """Should detect tool call pattern changes."""
        comparator = DriftComparator()

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
        comparator = DriftComparator()

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
