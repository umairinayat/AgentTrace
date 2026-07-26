"""Shared test fixtures for AgentTrace SDK tests."""

from __future__ import annotations

import pytest

from agenttrace import tracer as global_tracer
from agenttrace.client import TraceClient
from agenttrace.tracer import Tracer


@pytest.fixture
def tracer() -> Tracer:
    """Create a fresh tracer instance for testing."""
    t = Tracer()
    t.init(collector_url="http://localhost:8000")
    return t


@pytest.fixture
def client() -> TraceClient:
    """Create a fresh client for testing."""
    return TraceClient(collector_url="http://localhost:8000")


@pytest.fixture
def captured(monkeypatch: pytest.MonkeyPatch) -> list:
    """Init the GLOBAL tracer and capture spans emitted to it.

    Integrations look up the singleton via ``from agenttrace import tracer``, so
    tests that exercise them must patch the global instance, not a fresh one.
    """
    global_tracer.init(collector_url="http://localhost:8000")
    collected: list = []
    monkeypatch.setattr(global_tracer, "_emit", collected.append)
    return collected
