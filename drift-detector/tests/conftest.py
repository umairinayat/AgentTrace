"""Shared fixtures for drift detector tests."""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from detector.models import BaselineRecord, DriftConfig


class FakeEmbedder:
    """Deterministic stand-in for sentence-transformers.

    Maps known texts to preset vectors (so tests control cosine distance
    exactly) and unknown texts to a zero vector. This lets the semantic-drift
    code path run in CI without loading the 80MB model (or TensorFlow).
    """

    def __init__(self, dim: int = 4) -> None:
        self._dim = dim
        self._vecs: dict[str, np.ndarray] = {}

    def set(self, text: str, vector: list[float] | np.ndarray) -> FakeEmbedder:
        vec = np.array(vector, dtype=float)
        self._vecs[text] = vec
        return self

    def encode(self, texts: list[str], show_progress_bar: bool = False) -> np.ndarray:
        del show_progress_bar  # match the sentence-transformers API
        zero = np.zeros(self._dim)
        return np.array([self._vecs.get(t, zero) for t in texts])


@pytest.fixture
def fake_embedder() -> FakeEmbedder:
    """A fresh fake embedder for tests."""
    return FakeEmbedder()


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


def make_spans(
    agent: str,
    n: int,
    response: str = "hello",
    tokens: int = 100,
    latency: float = 100.0,
) -> list[dict[str, Any]]:
    """Build n llm_call span dicts as the collector would serve them."""
    return [
        {
            "event_type": "llm_call",
            "agent_name": agent,
            "latency_ms": latency,
            "total_tokens": tokens,
            "output_data": {"response": response},
            "input_data": {},
        }
        for _ in range(n)
    ]

