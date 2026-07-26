"""Ollama integration via httpx event hooks.

Intercepts HTTP calls to the Ollama API to capture LLM call spans.
"""

from __future__ import annotations

import contextlib
import json
import logging
import time
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx

from agenttrace.context import get_current_context
from agenttrace.models import SpanEvent
from agenttrace.pricing import estimate_cost

logger = logging.getLogger(__name__)

# Ollama default endpoints
_OLLAMA_CHAT_PATH = "/api/chat"
_OLLAMA_GENERATE_PATH = "/api/generate"


class OllamaTracingTransport(httpx.BaseTransport):
    """httpx transport wrapper that traces Ollama API calls.

    Usage:
        from agenttrace import tracer
        from agenttrace.integrations.ollama import traced_ollama_client

        tracer.init(collector_url="http://localhost:8000")
        client = traced_ollama_client()

        # Use client as normal httpx client for Ollama
        response = client.post("http://localhost:11434/api/chat", json={...})
    """

    def __init__(self, transport: httpx.BaseTransport | None = None) -> None:
        self._transport = transport or httpx.HTTPTransport()

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path

        if path not in (_OLLAMA_CHAT_PATH, _OLLAMA_GENERATE_PATH):
            return self._transport.handle_request(request)

        from agenttrace import tracer as _tracer

        if not _tracer._initialized:
            return self._transport.handle_request(request)

        ctx = get_current_context()
        trace_id = ctx.trace_id if ctx else str(uuid.uuid4())
        span_id = str(uuid.uuid4())

        # Parse request body
        body: dict[str, Any] = {}
        if request.content:
            with contextlib.suppress(json.JSONDecodeError, UnicodeDecodeError):
                body = json.loads(request.content)

        # Streaming responses cannot be read here without consuming the caller's
        # stream, so we skip response capture for streamed requests.
        is_stream = bool(body.get("stream", False))

        model = body.get("model", "ollama")
        prompt = ""
        if "messages" in body:
            msgs = body["messages"]
            prompt = msgs[-1].get("content", "")[:500] if msgs else ""
        elif "prompt" in body:
            prompt = str(body["prompt"])[:500]

        start = time.monotonic()
        error_msg = None
        response = None
        response_text = None
        prompt_tokens = None
        completion_tokens = None
        total_tokens = None

        try:
            response = self._transport.handle_request(request)
            return response
        except Exception as exc:
            error_msg = str(exc)
            raise
        finally:
            latency = (time.monotonic() - start) * 1000

            if response and response.status_code == 200 and not is_stream:
                try:
                    resp_body = json.loads(response.content)
                    if "message" in resp_body:
                        response_text = resp_body["message"].get("content", "")[:500]
                    elif "response" in resp_body:
                        response_text = str(resp_body["response"])[:500]

                    if "eval_count" in resp_body:
                        completion_tokens = resp_body.get("eval_count")
                        prompt_tokens = resp_body.get("prompt_eval_count")
                        if prompt_tokens and completion_tokens:
                            total_tokens = prompt_tokens + completion_tokens
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass

            cost = estimate_cost(model, prompt_tokens, completion_tokens)

            event = SpanEvent(
                trace_id=trace_id,
                span_id=span_id,
                parent_span_id=ctx.parent_span_id if ctx else None,
                agent_name="ollama_agent",
                event_type="llm_call",
                started_at=datetime.now(UTC),
                latency_ms=latency,
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost_usd=cost,
                input_data={"prompt": prompt},
                output_data={"response": response_text},
                error=error_msg,
            )
            _tracer._emit(event)


def traced_ollama_client(
    base_url: str = "http://localhost:11434",
    **kwargs: Any,
) -> httpx.Client:
    """Create an httpx client that traces Ollama API calls.

    Args:
        base_url: Ollama server URL.
        **kwargs: Extra arguments passed to httpx.Client.

    Returns:
        An httpx.Client configured with tracing transport.
    """
    transport = OllamaTracingTransport(httpx.HTTPTransport())
    return httpx.Client(base_url=base_url, transport=transport, **kwargs)
