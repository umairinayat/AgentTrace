"""Async context variables for trace propagation across coroutines."""

from __future__ import annotations

from contextvars import ContextVar
from typing import Optional

from agenttrace.models import TraceContext

# Global context variable for async trace propagation
_trace_context_var: ContextVar[Optional[TraceContext]] = ContextVar(
    "agenttrace_context", default=None
)


def get_current_context() -> Optional[TraceContext]:
    """Get the current trace context from the async context variable."""
    return _trace_context_var.get()


def set_current_context(ctx: Optional[TraceContext]) -> None:
    """Set the current trace context in the async context variable."""
    _trace_context_var.set(ctx)


def get_trace_id() -> Optional[str]:
    """Get the current trace ID from context."""
    ctx = get_current_context()
    return ctx.trace_id if ctx else None


def get_parent_span_id() -> Optional[str]:
    """Get the current parent span ID from context."""
    ctx = get_current_context()
    return ctx.parent_span_id if ctx else None


def get_agent_name() -> Optional[str]:
    """Get the current agent name from context."""
    ctx = get_current_context()
    return ctx.agent_name if ctx else None
