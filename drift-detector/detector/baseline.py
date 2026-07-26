"""Baseline builder for behavioral drift detection."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import numpy as np

from detector.models import BaselineRecord

logger = logging.getLogger(__name__)


class BaselineBuilder:
    """Builds statistical baselines from agent response data.

    Uses sentence-transformers to compute embedding centroids
    for semantic similarity comparison.
    """

    def __init__(
        self,
        embedding_model: str = "all-MiniLM-L6-v2",
        embedder: Any | None = None,
    ) -> None:
        """Initialize with the specified embedding model.

        Args:
            embedding_model: SentenceTransformer model name (80MB, runs on CPU).
            embedder: Optional pre-built embedder with an ``encode(texts)``
                method. Injected in tests to avoid loading the 80MB model.
        """
        self._model_name = embedding_model
        self._embedder = embedder

    def _get_embedder(self) -> Any:
        """Lazy-load the embedding model."""
        if self._embedder is None:
            from sentence_transformers import SentenceTransformer
            self._embedder = SentenceTransformer(self._model_name)
            logger.info("Loaded embedding model: %s", self._model_name)
        return self._embedder

    def build(
        self,
        agent_name: str,
        response_texts: list[str],
        latencies: list[float],
        token_counts: list[int],
        tool_calls: list[str],
    ) -> BaselineRecord:
        """Build a baseline from collected span data.

        Args:
            agent_name: Name of the agent.
            response_texts: List of response texts from LLM calls.
            latencies: List of latency values in ms.
            token_counts: List of total token counts.
            tool_calls: List of tool names called.

        Returns:
            BaselineRecord with computed statistics and embedding centroid.
        """
        n_samples = len(response_texts)
        if n_samples == 0:
            raise ValueError("Cannot build baseline with 0 samples")

        # Compute embeddings
        embedder = self._get_embedder()
        embeddings = embedder.encode(response_texts, show_progress_bar=False)
        centroid = np.mean(embeddings, axis=0).tolist()

        # Response length distribution
        response_lengths = [float(len(text)) for text in response_texts]
        avg_response_length = float(np.mean(response_lengths))

        # Latency stats
        avg_latency = float(np.mean(latencies)) if latencies else 0.0

        # Token stats
        avg_tokens = float(np.mean(token_counts)) if token_counts else 0.0

        # Tool call distribution
        tool_dist: dict[str, float] = {}
        if tool_calls:
            total = len(tool_calls)
            for tool in tool_calls:
                tool_dist[tool] = tool_dist.get(tool, 0) + 1
            tool_dist = {k: v / total for k, v in tool_dist.items()}

        baseline = BaselineRecord(
            agent_name=agent_name,
            built_at=datetime.now(UTC),
            n_samples=n_samples,
            avg_response_length=avg_response_length,
            avg_latency_ms=avg_latency,
            avg_token_count=avg_tokens,
            embedding_centroid=centroid,
            response_length_distribution=response_lengths,
            tool_call_distribution=tool_dist,
        )

        logger.info(
            "Built baseline for %s: %d samples, avg_length=%.1f, avg_tokens=%.1f",
            agent_name,
            n_samples,
            avg_response_length,
            avg_tokens,
        )
        return baseline
