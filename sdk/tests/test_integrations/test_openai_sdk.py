"""Tests for the OpenAI SDK integration (ChatCompletions.create patch)."""

from __future__ import annotations

import sys
import types
from types import SimpleNamespace

import pytest


def _install_fake_openai(monkeypatch: pytest.MonkeyPatch) -> None:
    openai = types.ModuleType("openai")
    resources = types.ModuleType("openai.resources")
    chat = types.ModuleType("openai.resources.chat")
    completions = types.ModuleType("openai.resources.chat.completions")

    class Completions:
        def create(self, *args: object, **kwargs: object) -> SimpleNamespace:
            return SimpleNamespace(
                usage=SimpleNamespace(prompt_tokens=5, completion_tokens=3, total_tokens=8),
                choices=[SimpleNamespace(message=SimpleNamespace(content="Hello!"))],
            )

    completions.Completions = Completions
    chat.completions = completions
    resources.chat = chat
    openai.resources = resources

    monkeypatch.setitem(sys.modules, "openai", openai)
    monkeypatch.setitem(sys.modules, "openai.resources", resources)
    monkeypatch.setitem(sys.modules, "openai.resources.chat", chat)
    monkeypatch.setitem(sys.modules, "openai.resources.chat.completions", completions)


def test_patch_traces_create(monkeypatch: pytest.MonkeyPatch, captured: list) -> None:
    """A patched Completions.create emits an llm_call span with usage and cost."""
    _install_fake_openai(monkeypatch)

    import agenttrace.integrations.openai_sdk as openai_integration

    openai_integration.patch_openai()

    from openai.resources.chat.completions import Completions

    result = Completions().create(
        model="gpt-4o", messages=[{"role": "user", "content": "hi"}]
    )
    assert result.usage.total_tokens == 8

    assert len(captured) == 1
    event = captured[0]
    assert event.event_type == "llm_call"
    assert event.model == "gpt-4o"
    assert event.prompt_tokens == 5
    assert event.total_tokens == 8
    assert event.cost_usd is not None  # gpt-4o is in pricing.json


def test_patch_is_idempotent(monkeypatch: pytest.MonkeyPatch, captured: list) -> None:
    """Patching twice does not double-wrap create."""
    _install_fake_openai(monkeypatch)

    import agenttrace.integrations.openai_sdk as openai_integration

    openai_integration.patch_openai()
    openai_integration.patch_openai()  # second call is a no-op

    from openai.resources.chat.completions import Completions

    Completions().create(model="gpt-4o", messages=[{"role": "user", "content": "hi"}])
    assert len(captured) == 1  # exactly one span, not two
