"""Tests for the baseline builder."""

from __future__ import annotations

import pytest

from detector.baseline import BaselineBuilder


class TestBaselineBuilder:
    """Test BaselineBuilder functionality."""

    def test_build_creates_baseline(self, fake_embedder) -> None:
        """Builder should create a valid baseline from response data."""
        fake_embedder.set("Hello world", [1.0, 0.0, 0.0, 0.0])
        fake_embedder.set("How are you", [0.0, 1.0, 0.0, 0.0])
        fake_embedder.set("Fine thanks", [0.0, 0.0, 1.0, 0.0])
        builder = BaselineBuilder(embedder=fake_embedder)
        baseline = builder.build(
            agent_name="test_agent",
            response_texts=["Hello world", "How are you", "Fine thanks"],
            latencies=[100.0, 150.0, 120.0],
            token_counts=[50, 60, 55],
            tool_calls=["search", "search", "calculator"],
        )

        assert baseline.agent_name == "test_agent"
        assert baseline.n_samples == 3
        assert baseline.avg_response_length > 0
        assert baseline.avg_latency_ms == pytest.approx(123.33, abs=0.1)
        assert baseline.avg_token_count == pytest.approx(55.0)
        assert len(baseline.embedding_centroid) == fake_embedder._dim
        assert len(baseline.response_length_distribution) == 3
        assert "search" in baseline.tool_call_distribution
        assert baseline.tool_call_distribution["search"] == pytest.approx(2 / 3)

    def test_build_empty_raises(self) -> None:
        """Builder should raise ValueError with no samples."""
        builder = BaselineBuilder()
        with pytest.raises(ValueError, match="Cannot build baseline with 0 samples"):
            builder.build(
                agent_name="test",
                response_texts=[],
                latencies=[],
                token_counts=[],
                tool_calls=[],
            )

    def test_build_no_tools(self, fake_embedder) -> None:
        """Builder should handle missing tool calls."""
        fake_embedder.set("Hello world", [1.0, 0.0, 0.0, 0.0])
        builder = BaselineBuilder(embedder=fake_embedder)
        baseline = builder.build(
            agent_name="test_agent",
            response_texts=["Hello world"],
            latencies=[100.0],
            token_counts=[50],
            tool_calls=[],
        )

        assert baseline.tool_call_distribution == {}
