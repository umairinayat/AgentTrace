"""CrewAI integration via monkey-patching Agent.execute_task."""

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


def patch_crewai() -> None:
    """Monkey-patch CrewAI's Agent.execute_task to capture traces.

    Usage:
        from agenttrace import tracer
        from agenttrace.integrations.crewai import patch_crewai

        tracer.init(collector_url="http://localhost:8000")
        patch_crewai()

        # Your existing CrewAI code — unchanged
    """
    try:
        from crewai import Agent  # type: ignore[import-untyped]
    except ImportError:
        logger.warning("crewai is not installed — skipping patch")
        return

    if getattr(Agent, "_agenttrace_patched", False):
        return

    original_execute = Agent.execute_task

    @functools.wraps(original_execute)
    def traced_execute(self: Any, task: Any, *args: Any, **kwargs: Any) -> Any:
        from agenttrace import tracer as _tracer

        if not _tracer._initialized:
            return original_execute(self, task, *args, **kwargs)

        ctx = get_current_context()
        trace_id = ctx.trace_id if ctx else str(uuid.uuid4())
        span_id = str(uuid.uuid4())
        agent_name = getattr(self, "role", None) or getattr(self, "name", "crewai_agent")
        task_desc = str(getattr(task, "description", ""))

        start = time.monotonic()
        error_msg = None
        result = None
        try:
            result = original_execute(self, task, *args, **kwargs)
            return result
        except Exception as exc:
            error_msg = str(exc)
            raise
        finally:
            latency = (time.monotonic() - start) * 1000
            event = SpanEvent(
                trace_id=trace_id,
                span_id=span_id,
                parent_span_id=ctx.parent_span_id if ctx else None,
                agent_name=str(agent_name),
                event_type="agent_end",
                started_at=datetime.now(timezone.utc),
                latency_ms=latency,
                input_data={"task": task_desc},
                output_data={"result": str(result) if result else None},
                error=error_msg,
            )
            _tracer._emit(event)

    Agent.execute_task = traced_execute
    Agent._agenttrace_patched = True  # type: ignore[attr-defined]
    logger.info("CrewAI Agent.execute_task patched for AgentTrace")
