"""OpenAI Agents SDK integration via tracing hook.

Patches the OpenAI Agents SDK to capture agent execution spans
including tool calls, handoffs, and LLM completions.
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from agenttrace.context import get_current_context
from agenttrace.models import SpanEvent

logger = logging.getLogger(__name__)

_agenttrace_patched = False


def patch_openai_agents() -> None:
    """Patch the OpenAI Agents SDK to emit AgentTrace spans.

    This patches ``Runner.run`` to wrap each agent execution with
    tracing spans. The patch is idempotent.

    Usage:
        from agenttrace import tracer
        from agenttrace.integrations.openai_agents import patch_openai_agents

        tracer.init(collector_url="http://localhost:8000")
        patch_openai_agents()

        # Your existing OpenAI Agents code — unchanged
        from agents import Agent, Runner
        agent = Agent(name="my_agent", instructions="You are helpful.")
        result = Runner.run_sync(agent, "Hello!")
    """
    global _agenttrace_patched
    if _agenttrace_patched:
        return

    try:
        from agents import Runner
    except ImportError:
        logger.warning(
            "openai-agents package not installed. "
            "Install with: pip install openai-agents"
        )
        return

    _original_run = Runner.run

    async def _traced_run(
        starting_agent: Any,
        input: Any,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        from agenttrace import tracer as _tracer

        if not _tracer._initialized:
            return await _original_run(starting_agent, input, *args, **kwargs)

        ctx = get_current_context()
        trace_id = ctx.trace_id if ctx else str(uuid.uuid4())
        span_id = str(uuid.uuid4())

        agent_name = getattr(starting_agent, "name", "openai_agent")
        input_text = str(input)[:500] if input else ""

        start = time.monotonic()
        error_msg = None
        result = None

        try:
            result = await _original_run(starting_agent, input, *args, **kwargs)
            return result
        except Exception as exc:
            error_msg = str(exc)
            raise
        finally:
            latency = (time.monotonic() - start) * 1000

            output_text = ""
            if result is not None:
                final_output = getattr(result, "final_output", None)
                if final_output is not None:
                    output_text = str(final_output)[:500]

            model = getattr(starting_agent, "model", None) or "gpt-4o"

            event = SpanEvent(
                trace_id=trace_id,
                span_id=span_id,
                parent_span_id=ctx.parent_span_id if ctx else None,
                agent_name=agent_name,
                event_type="agent_end",
                started_at=datetime.now(UTC),
                latency_ms=latency,
                model=model,
                input_data={"input": input_text},
                output_data={"output": output_text},
                error=error_msg,
            )
            _tracer._emit(event)

    Runner.run = staticmethod(_traced_run)  # type: ignore[assignment]
    _agenttrace_patched = True
    logger.info("AgentTrace: OpenAI Agents SDK patched successfully")
