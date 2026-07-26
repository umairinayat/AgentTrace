"""OpenAI SDK integration via monkey-patching chat.completions.create."""

from __future__ import annotations

import functools
import logging
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from agenttrace.context import get_current_context
from agenttrace.models import SpanEvent
from agenttrace.pricing import estimate_cost

logger = logging.getLogger(__name__)


def patch_openai() -> None:
    """Monkey-patch OpenAI's ChatCompletions.create to capture traces.

    Usage:
        from agenttrace import tracer
        from agenttrace.integrations.openai_sdk import patch_openai

        tracer.init(collector_url="http://localhost:8000")
        patch_openai()

        # Your existing OpenAI code — unchanged
        client = openai.OpenAI()
        response = client.chat.completions.create(model="gpt-4o", messages=[...])
    """
    try:
        from openai.resources.chat import (
            completions as _completions,  # type: ignore[import-untyped]
        )
    except ImportError:
        logger.warning("openai is not installed — skipping patch")
        return

    cls = _completions.Completions

    if getattr(cls, "_agenttrace_patched", False):
        return

    original_create = cls.create

    @functools.wraps(original_create)
    def traced_create(self: Any, *args: Any, **kwargs: Any) -> Any:
        from agenttrace import tracer as _tracer

        if not _tracer._initialized:
            return original_create(self, *args, **kwargs)

        ctx = get_current_context()
        trace_id = ctx.trace_id if ctx else str(uuid.uuid4())
        span_id = str(uuid.uuid4())

        model = kwargs.get("model", "unknown")
        messages = kwargs.get("messages", [])
        input_summary = str(messages[-1].get("content", ""))[:500] if messages else ""

        start = time.monotonic()
        error_msg = None
        result = None
        try:
            result = original_create(self, *args, **kwargs)
            return result
        except Exception as exc:
            error_msg = str(exc)
            raise
        finally:
            latency = (time.monotonic() - start) * 1000

            prompt_tokens = None
            completion_tokens = None
            total_tokens = None
            response_text = None

            if result and hasattr(result, "usage") and result.usage:
                prompt_tokens = result.usage.prompt_tokens
                completion_tokens = result.usage.completion_tokens
                total_tokens = result.usage.total_tokens

            if result and hasattr(result, "choices") and result.choices:
                msg = result.choices[0].message
                response_text = msg.content if hasattr(msg, "content") else str(msg)

            cost = estimate_cost(model, prompt_tokens, completion_tokens)

            event = SpanEvent(
                trace_id=trace_id,
                span_id=span_id,
                parent_span_id=ctx.parent_span_id if ctx else None,
                agent_name="openai_agent",
                event_type="llm_call",
                started_at=datetime.now(UTC),
                latency_ms=latency,
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost_usd=cost,
                input_data={"prompt": input_summary},
                output_data={"response": response_text[:500] if response_text else None},
                error=error_msg,
            )
            _tracer._emit(event)

    cls.create = traced_create
    cls._agenttrace_patched = True  # type: ignore[attr-defined]
    logger.info("OpenAI ChatCompletions.create patched for AgentTrace")
