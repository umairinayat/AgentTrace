"""Core Tracer class -- the singleton entry point for all AgentTrace tracing."""

from __future__ import annotations

import asyncio
import atexit
import functools
import logging
import time
import uuid
from collections.abc import Callable, Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any, TypeVar

from agenttrace.client import TraceClient
from agenttrace.context import get_current_context, set_current_context
from agenttrace.models import SpanEvent, TraceContext
from agenttrace.pricing import estimate_cost
from agenttrace.queue import EventQueue

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


class SpanContext:
    """Context manager for creating and managing a span."""

    def __init__(
        self,
        tracer: Tracer,
        event_type: str,
        agent_name: str,
        trace_id: str | None = None,
        parent_span_id: str | None = None,
    ) -> None:
        self._tracer = tracer
        self.span_id = str(uuid.uuid4())
        self.trace_id = trace_id or str(uuid.uuid4())
        self.parent_span_id = parent_span_id
        self.agent_name = agent_name
        self.event_type = event_type
        self._start_time: float = 0
        self._started_at: datetime | None = None
        self._input_data: dict[str, object] | None = None
        self._output_data: dict[str, object] | None = None
        self._metadata: dict[str, object] | None = None
        self._model: str | None = None
        self._prompt_tokens: int | None = None
        self._completion_tokens: int | None = None
        self._total_tokens: int | None = None
        self._error: str | None = None
        self._previous_context: TraceContext | None = None

    def set_input(self, data: dict[str, object]) -> SpanContext:
        """Set the input data for this span."""
        self._input_data = data
        return self

    def set_output(self, data: dict[str, object]) -> SpanContext:
        """Set the output data for this span."""
        self._output_data = data
        return self

    def set_model(self, model: str) -> SpanContext:
        """Set the model name for this span."""
        self._model = model
        return self

    def set_tokens(
        self,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        total_tokens: int | None = None,
    ) -> SpanContext:
        """Set token counts for this span."""
        self._prompt_tokens = prompt_tokens
        self._completion_tokens = completion_tokens
        self._total_tokens = total_tokens or (
            (prompt_tokens or 0) + (completion_tokens or 0)
            if prompt_tokens or completion_tokens
            else None
        )
        return self

    def set_metadata(self, metadata: dict[str, object]) -> SpanContext:
        """Set additional metadata for this span."""
        self._metadata = metadata
        return self

    def set_error(self, error: str) -> SpanContext:
        """Record an error for this span."""
        self._error = error
        return self

    def __enter__(self) -> SpanContext:
        self._start_time = time.monotonic()
        self._started_at = datetime.now(UTC)

        # Save previous context and set new one
        self._previous_context = get_current_context()
        set_current_context(
            TraceContext(
                trace_id=self.trace_id,
                parent_span_id=self.span_id,
                agent_name=self.agent_name,
            )
        )
        return self

    def __exit__(
        self,
        exc_type: type | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> None:
        latency_ms = (time.monotonic() - self._start_time) * 1000
        ended_at = datetime.now(UTC)

        if exc_val is not None:
            self._error = str(exc_val)

        cost = estimate_cost(self._model, self._prompt_tokens, self._completion_tokens)

        event = SpanEvent(
            trace_id=self.trace_id,
            span_id=self.span_id,
            parent_span_id=self.parent_span_id,
            agent_name=self.agent_name,
            event_type=self.event_type,  # type: ignore[arg-type]
            started_at=self._started_at or datetime.now(UTC),
            ended_at=ended_at,
            latency_ms=latency_ms,
            model=self._model,
            prompt_tokens=self._prompt_tokens,
            completion_tokens=self._completion_tokens,
            total_tokens=self._total_tokens,
            cost_usd=cost,
            input_data=self._input_data,
            output_data=self._output_data,
            error=self._error,
            metadata=self._metadata,
        )

        self._tracer._emit(event)

        # Restore previous context
        set_current_context(self._previous_context)


class Tracer:
    """Singleton tracer for AgentTrace.

    Usage:
        tracer.init(collector_url="http://localhost:8000")

        with tracer.span("llm_call", agent_name="my_agent") as span:
            span.set_input({"prompt": "..."})
            result = call_llm(...)
            span.set_output({"response": result})
    """

    def __init__(self) -> None:
        self._client: TraceClient | None = None
        self._queue: EventQueue | None = None
        self._initialized = False
        self._batch_size = 10
        self._flush_interval = 2.0
        # Ensure spans emitted from synchronous code (no running event loop, e.g.
        # LangChain's sync .invoke()) are not lost -- flush on interpreter exit.
        atexit.register(self._atexit_flush)

    def init(
        self,
        collector_url: str = "http://localhost:8000",
        batch_size: int = 10,
        flush_interval: float = 2.0,
        api_key: str | None = None,
    ) -> None:
        """Initialize the tracer with collector connection details.

        Args:
            collector_url: Base URL of the AgentTrace Collector.
            batch_size: Number of events per batch flush.
            flush_interval: Seconds between automatic flushes.
            api_key: Optional API key for authentication.
        """
        if self._initialized:
            logger.warning("Tracer already initialized, re-initializing")

        self._client = TraceClient(
            collector_url=collector_url,
            api_key=api_key,
        )
        self._batch_size = batch_size
        self._flush_interval = flush_interval
        self._queue = EventQueue(
            client=self._client,
            batch_size=batch_size,
            flush_interval=flush_interval,
        )
        self._initialized = True
        logger.info("AgentTrace initialized: collector=%s", collector_url)

        # Start the flush loop if there's a running event loop
        try:
            asyncio.get_running_loop()
            self._queue.start()
        except RuntimeError:
            # No event loop running -- queue will be started on first emit
            pass

    def _ensure_initialized(self) -> None:
        """Ensure the tracer has been initialized."""
        if not self._initialized or self._queue is None:
            raise RuntimeError(
                "Tracer not initialized. Call tracer.init(collector_url='...') first."
            )

    def _emit(self, event: SpanEvent) -> None:
        """Emit a span event to the queue.

        If an event loop is running, the background flush loop is (re)started so
        the event is delivered asynchronously. With no running loop (synchronous
        caller), the event is buffered and delivered on the next ``flush_sync()``
        call or at interpreter exit -- it is never silently dropped.
        """
        self._ensure_initialized()
        assert self._queue is not None

        try:
            asyncio.get_running_loop()
            if not self._queue.is_running:
                self._queue.start()
        except RuntimeError:
            pass  # No running loop; event buffered, flushed on exit / flush_sync().

        self._queue.enqueue(event)

    @contextmanager
    def span(
        self,
        event_type: str = "llm_call",
        agent_name: str | None = None,
        trace_id: str | None = None,
        parent_span_id: str | None = None,
    ) -> Generator[SpanContext, None, None]:
        """Create a traced span as a context manager.

        Args:
            event_type: Type of event (llm_call, tool_call, agent_start, etc.)
            agent_name: Name of the agent producing this span.
            trace_id: Optional trace ID (auto-generated if not provided).
            parent_span_id: Optional parent span ID for nesting.

        Yields:
            SpanContext with methods to set input/output/model/tokens.
        """
        self._ensure_initialized()

        # Inherit from current context if not provided
        ctx = get_current_context()
        if ctx and not trace_id:
            trace_id = ctx.trace_id
        if ctx and not parent_span_id:
            parent_span_id = ctx.parent_span_id
        if ctx and not agent_name:
            agent_name = ctx.agent_name

        if not agent_name:
            agent_name = "unknown"

        span_ctx = SpanContext(
            tracer=self,
            event_type=event_type,
            agent_name=agent_name,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
        )

        with span_ctx:
            yield span_ctx

    def trace_agent(
        self, name: str | None = None
    ) -> Callable[[F], F]:
        """Decorator to trace an agent function (sync or async).

        Args:
            name: Agent name. Defaults to the function name.

        Returns:
            Decorated function with automatic tracing.
        """
        self._ensure_initialized()

        def decorator(func: F) -> F:
            agent_name = name or func.__name__

            if asyncio.iscoroutinefunction(func):

                @functools.wraps(func)
                async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                    with self.span("agent_start", agent_name=agent_name) as span:
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
                    with self.span("agent_start", agent_name=agent_name) as span:
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

    async def flush(self) -> None:
        """Manually flush all pending events."""
        if self._queue:
            await self._queue._flush_batch()

    async def shutdown(self) -> None:
        """Gracefully shutdown the tracer."""
        if self._queue:
            await self._queue.stop()
        if self._client:
            await self._client.close()
        self._initialized = False
        logger.info("AgentTrace tracer shut down")

    def flush_sync(self) -> None:
        """Flush pending events from synchronous code with no running loop.

        Spans emitted by synchronous integrations (e.g. LangChain's ``.invoke()``)
        are buffered because the async flush loop cannot run without an event loop.
        Call this to deliver them immediately, or rely on the automatic atexit
        flush when the program exits.
        """
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            pass  # No running loop -- safe to spin one up.
        else:
            return  # A loop is running; the async flusher will handle delivery.

        if not self._initialized or self._queue is None or self._queue.pending_count == 0:
            return

        try:
            asyncio.run(self._drain_pending())
        except Exception:
            logger.debug("Synchronous flush failed", exc_info=True)

    def _atexit_flush(self) -> None:
        """Best-effort flush of any buffered events when the interpreter exits."""
        self.flush_sync()

    async def _drain_pending(self) -> None:
        """Drain all queued events in a fresh event loop (sync flush path)."""
        assert self._queue is not None
        while self._queue.pending_count > 0:
            await self._queue._flush_batch()
        if self._client is not None:
            await self._client.close()
