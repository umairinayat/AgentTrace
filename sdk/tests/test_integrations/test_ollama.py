"""Tests for the Ollama httpx transport integration."""

from __future__ import annotations

import httpx
import pytest

from agenttrace import tracer


class _FakeTransport:
    """Inner transport returning a canned Ollama response."""

    def __init__(self, payload: dict, status: int = 200) -> None:
        self._payload = payload
        self._status = status

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(self._status, json=self._payload)


@pytest.fixture
def captured(monkeypatch: pytest.MonkeyPatch) -> list:
    tracer.init(collector_url="http://localhost:8000")
    collected: list = []
    monkeypatch.setattr(tracer, "_emit", collected.append)
    return collected


def test_chat_endpoint_is_traced_with_tokens(captured: list) -> None:
    """A non-streaming /api/chat call is traced with token counts and cost."""
    from agenttrace.integrations.ollama import OllamaTracingTransport

    payload = {
        "message": {"content": "Hello from the local model"},
        "eval_count": 10,
        "prompt_eval_count": 5,
    }
    transport = OllamaTracingTransport(_FakeTransport(payload))
    request = httpx.Request(
        "POST",
        "http://localhost:11434/api/chat",
        json={"model": "qwen3:14b", "messages": [{"role": "user", "content": "hi"}]},
    )

    response = transport.handle_request(request)
    assert response.status_code == 200

    assert len(captured) == 1
    event = captured[0]
    assert event.event_type == "llm_call"
    assert event.model == "qwen3:14b"
    assert event.prompt_tokens == 5
    assert event.completion_tokens == 10
    assert event.total_tokens == 15
    # qwen3:14b is a local model priced at 0 in pricing.json.
    assert event.cost_usd == 0.0


def test_streaming_request_skips_response_capture(captured: list) -> None:
    """stream=true must not consume the response body."""
    from agenttrace.integrations.ollama import OllamaTracingTransport

    transport = OllamaTracingTransport(_FakeTransport({"message": {"content": "x"}}))
    request = httpx.Request(
        "POST",
        "http://localhost:11434/api/generate",
        json={"model": "llama4-scout", "stream": True, "prompt": "hi"},
    )

    transport.handle_request(request)

    assert len(captured) == 1
    event = captured[0]
    assert event.total_tokens is None  # capture skipped for streams
    assert event.cost_usd is None


def test_unrelated_path_is_not_traced(captured: list) -> None:
    """Requests to non-Ollama paths pass through untraced."""
    from agenttrace.integrations.ollama import OllamaTracingTransport

    transport = OllamaTracingTransport(_FakeTransport({"ok": True}))
    request = httpx.Request("GET", "http://localhost:11434/api/tags")

    transport.handle_request(request)
    assert captured == []
