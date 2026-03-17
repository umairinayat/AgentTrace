"""LangChain integration via BaseCallbackHandler."""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from agenttrace.context import get_current_context, set_current_context
from agenttrace.models import SpanEvent, TraceContext
from agenttrace.pricing import estimate_cost

logger = logging.getLogger(__name__)


class AgentTraceCallback:
    """LangChain callback handler that captures LLM calls and tool executions.

    Usage:
        from agenttrace.integrations.langchain import AgentTraceCallback

        callback = AgentTraceCallback(agent_name="my_agent")
        chain = LLMChain(llm=llm, prompt=prompt, callbacks=[callback])
    """

    def __init__(
        self,
        agent_name: str = "langchain_agent",
        trace_id: Optional[str] = None,
    ) -> None:
        self.agent_name = agent_name
        self.trace_id = trace_id or str(uuid.uuid4())
        self._span_starts: dict[str, float] = {}
        self._span_prompts: dict[str, str] = {}
        self._span_models: dict[str, str] = {}

    def _get_tracer(self) -> Any:
        """Get the global tracer instance."""
        from agenttrace import tracer
        return tracer

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        *,
        run_id: Optional[Any] = None,
        **kwargs: Any,
    ) -> None:
        """Record the start of an LLM call."""
        span_id = str(run_id) if run_id else str(uuid.uuid4())
        self._span_starts[span_id] = time.monotonic()
        self._span_prompts[span_id] = prompts[0] if prompts else ""

        # Extract model name from serialized or kwargs
        model_name = kwargs.get("invocation_params", {}).get("model_name", "")
        if not model_name:
            model_name = serialized.get("kwargs", {}).get("model_name", "unknown")
        self._span_models[span_id] = model_name

    def on_llm_end(
        self,
        response: Any,
        *,
        run_id: Optional[Any] = None,
        **kwargs: Any,
    ) -> None:
        """Record the end of an LLM call with response and token counts."""
        span_id = str(run_id) if run_id else ""
        start_time = self._span_starts.pop(span_id, time.monotonic())
        latency = (time.monotonic() - start_time) * 1000

        prompt_text = self._span_prompts.pop(span_id, "")
        model = self._span_models.pop(span_id, "unknown")

        # Extract token usage
        prompt_tokens = None
        completion_tokens = None
        total_tokens = None
        response_text = ""

        if hasattr(response, "llm_output") and response.llm_output:
            usage = response.llm_output.get("token_usage", {})
            prompt_tokens = usage.get("prompt_tokens")
            completion_tokens = usage.get("completion_tokens")
            total_tokens = usage.get("total_tokens")

        if hasattr(response, "generations") and response.generations:
            gen = response.generations[0]
            if gen:
                response_text = gen[0].text if hasattr(gen[0], "text") else str(gen[0])

        cost = estimate_cost(model, prompt_tokens, completion_tokens)

        ctx = get_current_context()
        event = SpanEvent(
            trace_id=self.trace_id,
            span_id=span_id or str(uuid.uuid4()),
            parent_span_id=ctx.parent_span_id if ctx else None,
            agent_name=self.agent_name,
            event_type="llm_call",
            started_at=datetime.now(timezone.utc),
            latency_ms=latency,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=cost,
            input_data={"prompt": prompt_text},
            output_data={"response": response_text},
        )

        tracer = self._get_tracer()
        tracer._emit(event)

    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: Optional[Any] = None,
        **kwargs: Any,
    ) -> None:
        """Record an LLM error."""
        span_id = str(run_id) if run_id else str(uuid.uuid4())
        start_time = self._span_starts.pop(span_id, time.monotonic())
        latency = (time.monotonic() - start_time) * 1000

        event = SpanEvent(
            trace_id=self.trace_id,
            span_id=span_id,
            agent_name=self.agent_name,
            event_type="error",
            latency_ms=latency,
            error=str(error),
        )

        tracer = self._get_tracer()
        tracer._emit(event)

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: Optional[Any] = None,
        **kwargs: Any,
    ) -> None:
        """Record the start of a tool call."""
        span_id = str(run_id) if run_id else str(uuid.uuid4())
        self._span_starts[span_id] = time.monotonic()
        self._span_prompts[span_id] = input_str

    def on_tool_end(
        self,
        output: str,
        *,
        run_id: Optional[Any] = None,
        **kwargs: Any,
    ) -> None:
        """Record the end of a tool call."""
        span_id = str(run_id) if run_id else ""
        start_time = self._span_starts.pop(span_id, time.monotonic())
        latency = (time.monotonic() - start_time) * 1000
        input_str = self._span_prompts.pop(span_id, "")

        event = SpanEvent(
            trace_id=self.trace_id,
            span_id=span_id or str(uuid.uuid4()),
            agent_name=self.agent_name,
            event_type="tool_end",
            latency_ms=latency,
            input_data={"tool_input": input_str},
            output_data={"tool_output": output},
        )

        tracer = self._get_tracer()
        tracer._emit(event)

    def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: Optional[Any] = None,
        **kwargs: Any,
    ) -> None:
        """Record a tool error."""
        span_id = str(run_id) if run_id else str(uuid.uuid4())
        start_time = self._span_starts.pop(span_id, time.monotonic())
        latency = (time.monotonic() - start_time) * 1000

        event = SpanEvent(
            trace_id=self.trace_id,
            span_id=span_id,
            agent_name=self.agent_name,
            event_type="error",
            latency_ms=latency,
            error=str(error),
        )

        tracer = self._get_tracer()
        tracer._emit(event)
