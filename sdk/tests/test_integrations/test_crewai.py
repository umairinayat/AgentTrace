"""Tests for the CrewAI integration (Agent.execute_task patch)."""

from __future__ import annotations

import sys
import types

import pytest

from agenttrace import tracer


def _install_fake_crewai(monkeypatch: pytest.MonkeyPatch) -> types.ModuleType:
    crewai = types.ModuleType("crewai")

    class Agent:
        def execute_task(self, task: object, *args: object, **kwargs: object) -> str:
            desc = getattr(task, "description", "")
            return f"done:{desc}"

    crewai.Agent = Agent
    monkeypatch.setitem(sys.modules, "crewai", crewai)
    return crewai


def test_patch_traces_execute_task(
    monkeypatch: pytest.MonkeyPatch, captured: list
) -> None:
    """A patched Agent.execute_task emits an agent_end span with task context."""
    _install_fake_crewai(monkeypatch)

    import agenttrace.integrations.crewai as crewai_integration

    crewai_integration.patch_crewai()

    from crewai import Agent

    agent = Agent()
    agent.role = "researcher"  # type: ignore[attr-defined]
    task = types.SimpleNamespace(description="find relevant papers")

    result = agent.execute_task(task)
    assert result == "done:find relevant papers"

    assert len(captured) == 1
    event = captured[0]
    assert event.event_type == "agent_end"
    assert event.agent_name == "researcher"
    assert event.input_data == {"task": "find relevant papers"}


def test_bails_out_when_tracer_uninitialized(monkeypatch: pytest.MonkeyPatch) -> None:
    """If the tracer isn't initialized, the original method runs untraced."""
    _install_fake_crewai(monkeypatch)

    import agenttrace.integrations.crewai as crewai_integration

    crewai_integration.patch_crewai()

    # Force uninitialized AFTER patching.
    monkeypatch.setattr(tracer, "_initialized", False)

    from crewai import Agent

    result = Agent().execute_task(types.SimpleNamespace(description="x"))
    assert result == "done:x"
