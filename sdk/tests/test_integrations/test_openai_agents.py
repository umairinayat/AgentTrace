"""Tests for the OpenAI Agents SDK integration.

These do not require the real ``openai-agents`` package; a stub ``agents``
module is injected so the patch logic and the emitted ``SpanEvent`` shape can be
verified -- notably that ``event_type`` is a valid literal, not the old invalid
``agent_action`` which raised ``ValidationError`` on every traced run.
"""

from __future__ import annotations

import asyncio
import sys
import types

import pytest

from agenttrace import tracer


@pytest.fixture
def fake_agents(monkeypatch: pytest.MonkeyPatch) -> types.ModuleType:
    """Inject a minimal fake ``agents`` package exposing ``Runner.run``."""

    agents = types.ModuleType("agents")

    class _Result:
        def __init__(self, output: str) -> None:
            self.final_output = output

    async def fake_run(
        starting_agent: object, input: object, *args: object, **kwargs: object
    ) -> _Result:
        return _Result("fake output")

    class Runner:
        run = staticmethod(fake_run)

    agents.Runner = Runner
    monkeypatch.setitem(sys.modules, "agents", agents)
    return agents


def test_patch_emits_valid_event_type(
    fake_agents: types.ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A traced OpenAI Agents run must emit a span with a valid event_type."""
    tracer.init(collector_url="http://localhost:8000")
    collected: list = []
    monkeypatch.setattr(tracer, "_emit", collected.append)

    import agenttrace.integrations.openai_agents as oa

    monkeypatch.setattr(oa, "_agenttrace_patched", False)
    oa.patch_openai_agents()

    starting_agent = types.SimpleNamespace(name="my_agent", model="gpt-4o")
    asyncio.run(fake_agents.Runner.run(starting_agent, "Hello"))  # type: ignore[attr-defined]

    assert len(collected) == 1
    event = collected[0]
    assert event.event_type == "agent_end"  # valid SpanEvent literal
    assert event.agent_name == "my_agent"
    assert event.model == "gpt-4o"


def test_invalid_event_type_rejected() -> None:
    """Guard the SpanEvent Literal: the old 'agent_action' must be rejected."""
    from pydantic import ValidationError

    from agenttrace.models import SpanEvent

    with pytest.raises(ValidationError):
        SpanEvent(agent_name="x", event_type="agent_action")  # type: ignore[arg-type]
