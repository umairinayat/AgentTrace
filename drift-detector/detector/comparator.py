"""Drift comparator -- compares current behavior against baseline."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import numpy as np
from scipy import stats as scipy_stats
from sklearn.metrics.pairwise import cosine_similarity

from detector.models import BaselineRecord, DriftAlert, DriftConfig, DriftReport

logger = logging.getLogger(__name__)


class DriftComparator:
    """Compares recent agent behavior against a stored baseline.

    Uses four complementary detection methods:
    1. Semantic drift (embedding cosine similarity)
    2. Response length distribution (Kolmogorov-Smirnov test)
    3. Token count anomaly (relative change)
    4. Tool call pattern changes (relative change)
    """

    def __init__(self, embedding_model: str = "all-MiniLM-L6-v2") -> None:
        self._model_name = embedding_model
        self._embedder: Any = None

    def _get_embedder(self) -> Any:
        """Lazy-load the embedding model."""
        if self._embedder is None:
            from sentence_transformers import SentenceTransformer
            self._embedder = SentenceTransformer(self._model_name)
        return self._embedder

    def compare(
        self,
        baseline: BaselineRecord,
        recent_texts: list[str],
        recent_latencies: list[float],
        recent_token_counts: list[int],
        recent_tool_calls: list[str],
        config: DriftConfig | None = None,
    ) -> DriftReport:
        """Compare recent behavior against baseline.

        Args:
            baseline: The stored baseline record.
            recent_texts: Recent response texts.
            recent_latencies: Recent latency values.
            recent_token_counts: Recent token counts.
            recent_tool_calls: Recent tool call names.
            config: Drift detection thresholds.

        Returns:
            DriftReport with any detected alerts.
        """
        if config is None:
            config = DriftConfig()

        alerts: list[DriftAlert] = []
        cosine_dist: float | None = None
        ks_p_value: float | None = None
        token_pct_change: float | None = None

        agent_name = baseline.agent_name

        # Check 1: Semantic drift (embedding cosine similarity)
        if recent_texts and baseline.embedding_centroid:
            embedder = self._get_embedder()
            recent_embeddings = embedder.encode(recent_texts, show_progress_bar=False)
            recent_centroid = np.mean(recent_embeddings, axis=0).reshape(1, -1)
            baseline_centroid = np.array(baseline.embedding_centroid).reshape(1, -1)

            similarity = cosine_similarity(baseline_centroid, recent_centroid)[0][0]
            cosine_dist = float(1 - similarity)

            if cosine_dist > config.semantic_threshold:
                severity = "critical" if cosine_dist > config.semantic_threshold * 2 else "warning"
                alerts.append(
                    DriftAlert(
                        agent_name=agent_name,
                        alert_type="semantic",
                        severity=severity,
                        score=cosine_dist,
                        threshold=config.semantic_threshold,
                        description=f"Semantic drift detected: cosine distance = {cosine_dist:.3f}",
                    )
                )

        # Check 2: Response length distribution (KS test)
        if recent_texts and baseline.response_length_distribution:
            recent_lengths = [float(len(t)) for t in recent_texts]
            ks_stat, p_value = scipy_stats.ks_2samp(
                baseline.response_length_distribution, recent_lengths
            )
            ks_p_value = float(p_value)

            if p_value < config.ks_pvalue_threshold:
                alerts.append(
                    DriftAlert(
                        agent_name=agent_name,
                        alert_type="distribution",
                        severity="warning",
                        score=float(ks_stat),
                        threshold=config.ks_pvalue_threshold,
                        description=(
                            f"Response length distribution shifted: KS p-value = {p_value:.4f}"
                        ),
                    )
                )

        # Check 3: Token count anomaly
        if recent_token_counts and baseline.avg_token_count > 0:
            recent_avg_tokens = float(np.mean(recent_token_counts))
            pct_change = abs(recent_avg_tokens - baseline.avg_token_count) / baseline.avg_token_count
            token_pct_change = float(pct_change)

            if pct_change > config.token_change_threshold:
                alerts.append(
                    DriftAlert(
                        agent_name=agent_name,
                        alert_type="token",
                        severity="warning",
                        score=pct_change,
                        threshold=config.token_change_threshold,
                        description=f"Token usage changed by {pct_change * 100:.1f}%",
                    )
                )

        # Check 4: Tool call pattern changes
        if recent_tool_calls and baseline.tool_call_distribution:
            recent_dist: dict[str, float] = {}
            total = len(recent_tool_calls)
            for tool in recent_tool_calls:
                recent_dist[tool] = recent_dist.get(tool, 0) + 1
            recent_dist = {k: v / total for k, v in recent_dist.items()}

            all_tools = set(baseline.tool_call_distribution.keys()) | set(recent_dist.keys())
            max_change = 0.0
            for tool in all_tools:
                baseline_freq = baseline.tool_call_distribution.get(tool, 0)
                recent_freq = recent_dist.get(tool, 0)
                change = abs(baseline_freq - recent_freq)
                max_change = max(max_change, change)

            if max_change > config.tool_change_threshold:
                alerts.append(
                    DriftAlert(
                        agent_name=agent_name,
                        alert_type="tool",
                        severity="warning",
                        score=max_change,
                        threshold=config.tool_change_threshold,
                        description=f"Tool call pattern changed: max shift = {max_change:.2f}",
                    )
                )

        return DriftReport(
            agent_name=agent_name,
            checked_at=datetime.now(timezone.utc),
            alerts=alerts,
            is_drifted=len(alerts) > 0,
            cosine_distance=cosine_dist,
            ks_p_value=ks_p_value,
            token_pct_change=token_pct_change,
        )
