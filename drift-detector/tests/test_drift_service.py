"""Tests for the drift detector service orchestration.

These exercise the Phase-1A wiring (load/build/persist baselines, post alerts)
with the collector HTTP calls stubbed out and a fake embedder injected, so no
real collector or 80MB model is required.
"""

from __future__ import annotations

from typing import Any

import pytest

from detector.baseline import BaselineBuilder
from detector.main import DriftDetectorService


def _spans(
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


@pytest.mark.asyncio
async def test_builds_and_persists_baseline_when_none_exists(
    monkeypatch: pytest.MonkeyPatch, fake_embedder
) -> None:
    """First check with no baseline builds one and persists it; no alerts."""
    fake_embedder.set("hello", [1.0, 0.0, 0.0, 0.0])
    svc = DriftDetectorService(embedder=fake_embedder, check_interval=1)

    async def fetch(agent: str, limit: int = 50) -> list[dict[str, Any]]:
        return _spans(agent, 12)

    async def load(agent: str) -> None:
        return None

    persisted: list[Any] = []

    async def persist(baseline: Any) -> None:
        persisted.append(baseline)

    posted: list[dict[str, Any]] = []

    async def post(alert: dict[str, Any]) -> None:
        posted.append(alert)

    monkeypatch.setattr(svc, "_fetch_recent_spans", fetch)
    monkeypatch.setattr(svc, "_load_baseline", load)
    monkeypatch.setattr(svc, "_persist_baseline", persist)
    monkeypatch.setattr(svc, "_post_alert", post)

    await svc.check_agent("agent_a")

    assert len(persisted) == 1
    assert persisted[0].agent_name == "agent_a"
    assert posted == []  # build cycle does not compare


@pytest.mark.asyncio
async def test_posts_alert_when_behavior_drifts(
    monkeypatch: pytest.MonkeyPatch, fake_embedder
) -> None:
    """With an existing baseline and drifted spans, an alert is posted."""
    fake_embedder.set("baseline response", [1.0, 0.0, 0.0, 0.0])
    fake_embedder.set("drifted response", [0.0, 1.0, 0.0, 0.0])

    baseline = BaselineBuilder(embedder=fake_embedder).build(
        "agent_a", ["baseline response"] * 5, [100.0] * 5, [50] * 5, []
    )

    svc = DriftDetectorService(embedder=fake_embedder, check_interval=1)

    async def fetch(agent: str, limit: int = 50) -> list[dict[str, Any]]:
        return _spans(agent, 12, response="drifted response")

    async def load(agent: str) -> Any:
        return baseline

    async def persist(baseline: Any) -> None:
        pass

    posted: list[dict[str, Any]] = []

    async def post(alert: dict[str, Any]) -> None:
        posted.append(alert)

    monkeypatch.setattr(svc, "_fetch_recent_spans", fetch)
    monkeypatch.setattr(svc, "_load_baseline", load)
    monkeypatch.setattr(svc, "_persist_baseline", persist)
    monkeypatch.setattr(svc, "_post_alert", post)

    await svc.check_agent("agent_a")

    assert len(posted) >= 1
    assert any(a["alert_type"] == "semantic" for a in posted)


@pytest.mark.asyncio
async def test_skips_agent_with_too_few_samples(
    monkeypatch: pytest.MonkeyPatch, fake_embedder
) -> None:
    """Fewer than min_samples LLM spans skips baseline build and comparison."""
    svc = DriftDetectorService(embedder=fake_embedder, check_interval=1)

    async def fetch(agent: str, limit: int = 50) -> list[dict[str, Any]]:
        return _spans(agent, 3)  # below min_samples (10)

    called: dict[str, bool] = {"load": False, "persist": False}

    async def load(agent: str) -> None:
        called["load"] = True
        return None

    async def persist(baseline: Any) -> None:
        called["persist"] = True

    monkeypatch.setattr(svc, "_fetch_recent_spans", fetch)
    monkeypatch.setattr(svc, "_load_baseline", load)
    monkeypatch.setattr(svc, "_persist_baseline", persist)

    await svc.check_agent("agent_a")

    assert called == {"load": False, "persist": False}
