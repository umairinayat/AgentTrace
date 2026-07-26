"""LangGraph integration via StateGraph middleware patching."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable, Optional

from agenttrace.context import get_current_context
from agenttrace.models import SpanEvent, TraceContext

logger = logging.getLogger(__name__)

_patched = False
_original_add_node: Optional[Callable[..., Any]] = None


def patch_langgraph(
    agent_name: str = "langgraph_agent",
    trace_id: Optional[str] = None,
) -> None:
    """Patch LangGraph StateGraph to automatically trace all node executions.

    This monkey-patches the StateGraph.add_node method to wrap each node
    function with tracing.

    Args:
        agent_name: Default agent name for traces.
        trace_id: Optional shared trace ID.
    """
    global _patched
    if _patched:
        logger.warning("LangGraph already patched")
        return

    try:
        from langgraph.graph import StateGraph
    except ImportError:
        logger.error("langgraph not installed. Install with: pip install langgraph")
        raise

    # Stash the original so unpatch_langgraph can restore it in-process.
    original_add_node = StateGraph.add_node
    globals()["_original_add_node"] = original_add_node

    def patched_add_node(self: Any, node: str, action: Callable[..., Any], **kwargs: Any) -> Any:
        """Wrap node action with tracing."""
        wrapped = _wrap_node(action, node, agent_name, trace_id)
        return original_add_node(self, node, wrapped, **kwargs)

    StateGraph.add_node = patched_add_node  # type: ignore[assignment]
    _patched = True
    logger.info("LangGraph patched for AgentTrace tracing")


def _wrap_node(
    func: Callable[..., Any],
    node_name: str,
    agent_name: str,
    trace_id: Optional[str],
) -> Callable[..., Any]:
    """Wrap a LangGraph node function with span tracing."""

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        from agenttrace import tracer

        tid = trace_id or str(uuid.uuid4())
        ctx = get_current_context()
        if ctx:
            tid = ctx.trace_id

        with tracer.span(
            event_type="agent_start",
            agent_name=f"{agent_name}.{node_name}",
            trace_id=tid,
        ) as span:
            span.set_input({"node": node_name, "state": str(args[0]) if args else ""})
            try:
                result = func(*args, **kwargs)
                span.set_output({"result": str(result)})
                span.event_type = "agent_end"
                return result
            except Exception as exc:
                span.set_error(str(exc))
                span.event_type = "error"
                raise

    @wraps(func)
    async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
        from agenttrace import tracer

        tid = trace_id or str(uuid.uuid4())
        ctx = get_current_context()
        if ctx:
            tid = ctx.trace_id

        with tracer.span(
            event_type="agent_start",
            agent_name=f"{agent_name}.{node_name}",
            trace_id=tid,
        ) as span:
            span.set_input({"node": node_name, "state": str(args[0]) if args else ""})
            try:
                result = await func(*args, **kwargs)
                span.set_output({"result": str(result)})
                span.event_type = "agent_end"
                return result
            except Exception as exc:
                span.set_error(str(exc))
                span.event_type = "error"
                raise

    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return wrapper


def unpatch_langgraph() -> None:
    """Remove the LangGraph monkey-patch, restoring the original ``add_node``.

    Unlike the previous implementation, this fully reverses the patch in-process
    rather than requiring a restart.
    """
    global _patched, _original_add_node
    from langgraph.graph import StateGraph  # type: ignore[import-untyped]

    if _original_add_node is not None:
        StateGraph.add_node = _original_add_node  # type: ignore[assignment]
        _original_add_node = None
    _patched = False
    logger.info("LangGraph unpatched")
