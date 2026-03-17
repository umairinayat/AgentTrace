"""Convenience decorators for tracing agent functions."""

from __future__ import annotations

import asyncio
import functools
import logging
from typing import Any, Callable, Optional, TypeVar

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def trace_agent(
    name: Optional[str] = None,
    tracer: Optional[Any] = None,
) -> Callable[[F], F]:
    """Standalone decorator to trace an agent function.

    If no tracer is provided, uses the global singleton tracer.

    Args:
        name: Agent name. Defaults to the function name.
        tracer: Tracer instance. Uses global singleton if None.

    Returns:
        Decorated function with automatic tracing.
    """

    def decorator(func: F) -> F:
        agent_name = name or func.__name__

        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                from agenttrace import tracer as global_tracer

                t = tracer or global_tracer
                with t.span("agent_start", agent_name=agent_name) as span:
                    span.set_input({"args": str(args), "kwargs": str(kwargs)})
                    try:
                        result = await func(*args, **kwargs)
                        span.set_output({"result": str(result)})
                        span.event_type = "agent_end"
                        return result
                    except Exception as exc:
                        span.set_error(str(exc))
                        span.event_type = "error"
                        raise

            return async_wrapper  # type: ignore[return-value]
        else:

            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                from agenttrace import tracer as global_tracer

                t = tracer or global_tracer
                with t.span("agent_start", agent_name=agent_name) as span:
                    span.set_input({"args": str(args), "kwargs": str(kwargs)})
                    try:
                        result = func(*args, **kwargs)
                        span.set_output({"result": str(result)})
                        span.event_type = "agent_end"
                        return result
                    except Exception as exc:
                        span.set_error(str(exc))
                        span.event_type = "error"
                        raise

            return sync_wrapper  # type: ignore[return-value]

    return decorator
