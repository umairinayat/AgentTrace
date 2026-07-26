"""Tests for the AutoGen integration (ConversableAgent.generate_reply patch)."""

from __future__ import annotations

import sys
import types

import pytest


def _install_fake_autogen(monkeypatch: pytest.MonkeyPatch) -> None:
    autogen = types.ModuleType("autogen")
    agentchat = types.ModuleType("autogen.agentchat")

    class ConversableAgent:
        def generate_reply(
            self, messages: object | None = None, sender: object | None = None, **kwargs: object
        ) -> str:
            return "auto-reply"

    agentchat.ConversableAgent = ConversableAgent
    autogen.agentchat = agentchat
    monkeypatch.setitem(sys.modules, "autogen", autogen)
    monkeypatch.setitem(sys.modules, "autogen.agentchat", agentchat)


def test_patch_traces_generate_reply(
    monkeypatch: pytest.MonkeyPatch, captured: list
) -> None:
    """A patched generate_reply emits an llm_call span with the reply."""
    _install_fake_autogen(monkeypatch)

    import agenttrace.integrations.autogen as autogen_integration

    autogen_integration.patch_autogen()

    from autogen.agentchat import ConversableAgent

    agent = ConversableAgent()
    agent.name = "bob"  # type: ignore[attr-defined]
    result = agent.generate_reply(messages=[{"content": "hi"}], sender=None)
    assert result == "auto-reply"

    assert len(captured) == 1
    event = captured[0]
    assert event.event_type == "llm_call"
    assert event.agent_name == "bob"
    assert event.output_data == {"reply": "auto-reply"}


def test_patch_returns_without_autogen_installed(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """If autogen isn't importable, patch_autogen logs and returns cleanly."""
    # Ensure no autogen module resolves.
    monkeypatch.setitem(sys.modules, "autogen", None)
    monkeypatch.setitem(sys.modules, "autogen.agentchat", None)

    import agenttrace.integrations.autogen as autogen_integration

    autogen_integration.patch_autogen()  # must not raise
