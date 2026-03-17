"""Tests for the core Tracer class."""

from __future__ import annotations

import pytest

from agenttrace.tracer import Tracer


class TestTracer:
    """Tests for Tracer initialization and span creation."""

    def test_init(self) -> None:
        """Tracer should initialize correctly."""
        t = Tracer()
        t.init(collector_url="http://localhost:8000")
        assert t._initialized is True

    def test_not_initialized_raises(self) -> None:
        """Using tracer before init should raise RuntimeError."""
        t = Tracer()
        with pytest.raises(RuntimeError, match="not initialized"):
            with t.span("llm_call", agent_name="test"):
                pass

    def test_span_creates_event(self) -> None:
        """Span context manager should produce a SpanEvent."""
        t = Tracer()
        t.init(collector_url="http://localhost:8000")

        collected_events = []
        original_emit = t._emit

        def mock_emit(event):  # type: ignore[no-untyped-def]
            collected_events.append(event)

        t._emit = mock_emit  # type: ignore[assignment]

        with t.span("llm_call", agent_name="test_agent") as span:
            span.set_input({"prompt": "hello"})
            span.set_output({"response": "world"})
            span.set_model("gpt-4o")
            span.set_tokens(prompt_tokens=10, completion_tokens=5)

        assert len(collected_events) == 1
        event = collected_events[0]
        assert event.agent_name == "test_agent"
        assert event.event_type == "llm_call"
        assert event.model == "gpt-4o"
        assert event.prompt_tokens == 10
        assert event.latency_ms is not None
        assert event.latency_ms > 0

    def test_span_captures_error(self) -> None:
        """Span should capture exceptions."""
        t = Tracer()
        t.init(collector_url="http://localhost:8000")

        collected_events = []
        t._emit = lambda event: collected_events.append(event)  # type: ignore[assignment]

        with pytest.raises(ValueError, match="test error"):
            with t.span("llm_call", agent_name="test") as span:
                raise ValueError("test error")

        assert len(collected_events) == 1
        assert collected_events[0].error == "test error"

    def test_trace_agent_decorator_sync(self) -> None:
        """@trace_agent should trace sync functions."""
        t = Tracer()
        t.init(collector_url="http://localhost:8000")

        collected_events = []
        t._emit = lambda event: collected_events.append(event)  # type: ignore[assignment]

        @t.trace_agent(name="my_sync_agent")
        def my_func(x: int) -> int:
            return x * 2

        result = my_func(5)
        assert result == 10
        assert len(collected_events) == 1
        assert collected_events[0].agent_name == "my_sync_agent"

    @pytest.mark.asyncio
    async def test_trace_agent_decorator_async(self) -> None:
        """@trace_agent should trace async functions."""
        t = Tracer()
        t.init(collector_url="http://localhost:8000")

        collected_events = []
        t._emit = lambda event: collected_events.append(event)  # type: ignore[assignment]

        @t.trace_agent(name="my_async_agent")
        async def my_func(x: int) -> int:
            return x * 2

        result = await my_func(5)
        assert result == 10
        assert len(collected_events) == 1
        assert collected_events[0].agent_name == "my_async_agent"

    def test_nested_spans_propagate_context(self) -> None:
        """Nested spans should inherit trace_id from parent."""
        t = Tracer()
        t.init(collector_url="http://localhost:8000")

        collected_events = []
        t._emit = lambda event: collected_events.append(event)  # type: ignore[assignment]

        with t.span("agent_start", agent_name="parent") as parent_span:
            with t.span("llm_call", agent_name="child") as child_span:
                pass

        assert len(collected_events) == 2
        child_event = collected_events[0]
        parent_event = collected_events[1]
        # Child should inherit trace_id from parent
        assert child_event.trace_id == parent_event.trace_id
        # Child parent_span_id should point to parent's span_id
        assert child_event.parent_span_id == parent_span.span_id
