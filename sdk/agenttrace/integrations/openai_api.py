"""Raw OpenAI API integration via httpx transport.

Intercepts HTTP calls to the OpenAI API to capture LLM call spans,
similar to the Ollama integration. Works with any httpx-based client
targeting the OpenAI REST API directly (without the openai SDK).
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx

from agenttrace.context import get_current_context
from agenttrace.models import SpanEvent
from agenttrace.pricing import estimate_cost

logger = logging.getLogger(__name__)

_CHAT_COMPLETIONS_PATH = "/v1/chat/completions"
_COMPLETIONS_PATH = "/v1/completions"


class OpenAITracingTransport(httpx.BaseTransport):
    """httpx transport wrapper that traces raw OpenAI API calls.

    Usage:
        from agenttrace import tracer
        from agenttrace.integrations.openai_api import traced_openai_client

        tracer.init(collector_url="http://localhost:8000")
        client = traced_openai_client(api_key="sk-...")

        response = client.post("/v1/chat/completions", json={
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "Hello!"}],
        })
    """

    def __init__(self, transport: httpx.BaseTransport | None = None) -> None:
        self._transport = transport or httpx.HTTPTransport()

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path

        if path not in (_CHAT_COMPLETIONS_PATH, _COMPLETIONS_PATH):
            return self._transport.handle_request(request)

        from agenttrace import tracer as _tracer

        if not _tracer._initialized:
            return self._transport.handle_request(request)

        ctx = get_current_context()
        trace_id = ctx.trace_id if ctx else str(uuid.uuid4())
        span_id = str(uuid.uuid4())

        body: dict[str, Any] = {}
        if request.content:
            try:
                body = json.loads(request.content)
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass

        model = body.get("model", "openai")
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

            if response and response.status_code == 200:
                try:
                    resp_body = json.loads(response.content)
                    choices = resp_body.get("choices", [])
                    if choices:
                        choice = choices[0]
                        msg = choice.get("message", {})
                        response_text = msg.get("content", "")[:500]
                        if not response_text:
                            response_text = choice.get("text", "")[:500]

                    usage = resp_body.get("usage", {})
                    if usage:
                        prompt_tokens = usage.get("prompt_tokens")
                        completion_tokens = usage.get("completion_tokens")
                        total_tokens = usage.get("total_tokens")
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass

            cost = estimate_cost(model, prompt_tokens, completion_tokens)

            event = SpanEvent(
                trace_id=trace_id,
                span_id=span_id,
                parent_span_id=ctx.parent_span_id if ctx else None,
                agent_name="openai_agent",
                event_type="llm_call",
                started_at=datetime.now(timezone.utc),
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


def traced_openai_client(
    api_key: str = "",
    base_url: str = "https://api.openai.com",
    **kwargs: Any,
) -> httpx.Client:
    """Create an httpx client that traces raw OpenAI API calls.

    Args:
        api_key: OpenAI API key (set via header).
        base_url: OpenAI API base URL.
        **kwargs: Extra arguments passed to httpx.Client.

    Returns:
        An httpx.Client configured with tracing transport.
    """
    transport = OpenAITracingTransport(httpx.HTTPTransport())
    headers = kwargs.pop("headers", {})
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    headers.setdefault("Content-Type", "application/json")
    return httpx.Client(
        base_url=base_url,
        transport=transport,
        headers=headers,
        **kwargs,
    )
