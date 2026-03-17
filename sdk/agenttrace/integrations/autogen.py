"""AutoGen integration via monkey-patching ConversableAgent."""

from __future__ import annotations

import functools
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from agenttrace.context import get_current_context
from agenttrace.models import SpanEvent

logger = logging.getLogger(__name__)


def patch_autogen() -> None:
    """Monkey-patch AutoGen's ConversableAgent to capture traces.

    Usage:
        from agenttrace import tracer
        from agenttrace.integrations.autogen import patch_autogen

        tracer.init(collector_url="http://localhost:8000")
        patch_autogen()

        # Your existing AutoGen code — unchanged
    """
    try:
        from autogen import ConversableAgent  # type: ignore[import-untyped]
    except ImportError:
        logger.warning("autogen is not installed — skipping patch")
        return

    if getattr(ConversableAgent, "_agenttrace_patched", False):
        return

    original_generate = ConversableAgent.generate_reply

    @functools.wraps(original_generate)
    def traced_generate(self: Any, messages: Any = None, sender: Any = None, **kwargs: Any) -> Any:
        from agenttrace import tracer as _tracer

        if not _tracer._initialized:
            return original_generate(self, messages=messages, sender=sender, **kwargs)

        ctx = get_current_context()
        trace_id = ctx.trace_id if ctx else str(uuid.uuid4())
        span_id = str(uuid.uuid4())
        agent_name = getattr(self, "name", "autogen_agent")

        # Summarize input
        input_summary = None
        if messages:
            last_msg = messages[-1] if isinstance(messages, list) else messages
            input_summary = str(last_msg.get("content", ""))[:500] if isinstance(last_msg, dict) else str(last_msg)[:500]

        start = time.monotonic()
        error_msg = None
        result = None
        try:
            result = original_generate(self, messages=messages, sender=sender, **kwargs)
            return result
        except Exception as exc:
            error_msg = str(exc)
            raise
        finally:
            latency = (time.monotonic() - start) * 1000
            output = str(result)[:500] if result else None

            event = SpanEvent(
                trace_id=trace_id,
                span_id=span_id,
                parent_span_id=ctx.parent_span_id if ctx else None,
                agent_name=str(agent_name),
                event_type="llm_call",
                started_at=datetime.now(timezone.utc),
                latency_ms=latency,
                input_data={"messages": input_summary},
                output_data={"reply": output},
                error=error_msg,
            )
            _tracer._emit(event)

    ConversableAgent.generate_reply = traced_generate
    ConversableAgent._agenttrace_patched = True  # type: ignore[attr-defined]
    logger.info("AutoGen ConversableAgent.generate_reply patched for AgentTrace")
