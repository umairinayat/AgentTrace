"""Tests for the raw OpenAI API httpx transport integration."""

from __future__ import annotations

import httpx
import pytest

from agenttrace import tracer


class _FakeTransport:
    """Inner transport returning a canned chat-completion response."""

    def __init__(self, payload: dict, status: int = 200) -> None:
        self._payload = payload
        self._status = status

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(self._status, json=self._payload)


@pytest.fixture
def captured(monkeypatch: pytest.MonkeyPatch) -> list:
    """Init the global tracer and capture emitted spans."""
    tracer.init(collector_url="http://localhost:8000")
    collected: list = []
    monkeypatch.setattr(tracer, "_emit", collected.append)
    return collected


def test_transport_emits_llm_call_span_with_cost(captured: list) -> None:
    """A non-streaming chat completion is traced with tokens and cost."""
    from agenttrace.integrations.openai_api import OpenAITracingTransport

    payload = {
        "choices": [{"message": {"content": "Hello there"}}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
    }
    transport = OpenAITracingTransport(_FakeTransport(payload))
    request = httpx.Request(
        "POST",
        "https://api.openai.com/v1/chat/completions",
        json={"model": "gpt-4o", "messages": [{"role": "user", "content": "hi"}]},
    )

    response = transport.handle_request(request)
    assert response.status_code == 200

    assert len(captured) == 1
    event = captured[0]
    assert event.event_type == "llm_call"
    assert event.model == "gpt-4o"
    assert event.prompt_tokens == 5
    assert event.total_tokens == 8
    assert event.cost_usd is not None  # gpt-4o is in pricing.json


def test_transport_skips_response_capture_for_stream(captured: list) -> None:
    """Streaming requests must not consume the response body."""
    from agenttrace.integrations.openai_api import OpenAITracingTransport

    payload = {"choices": [{"message": {"content": "x"}}], "usage": {}}
    transport = OpenAITracingTransport(_FakeTransport(payload))
    request = httpx.Request(
        "POST",
        "https://api.openai.com/v1/chat/completions",
        json={"model": "gpt-4o", "stream": True, "messages": []},
    )

    transport.handle_request(request)

    assert len(captured) == 1
    event = captured[0]
    # Streaming: response capture was skipped, so no token/cost attribution.
    assert event.total_tokens is None
    assert event.cost_usd is None


def test_transport_passes_through_non_chat_paths(captured: list) -> None:
    """Requests to unrelated paths are forwarded without tracing."""
    from agenttrace.integrations.openai_api import OpenAITracingTransport

    transport = OpenAITracingTransport(_FakeTransport({"ok": True}))
    request = httpx.Request("GET", "https://api.openai.com/v1/models")

    response = transport.handle_request(request)
    assert response.status_code == 200
    assert captured == []  # nothing traced
