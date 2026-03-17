"""Tests for Pydantic models -- serialization and validation."""

from __future__ import annotations

from datetime import datetime, timezone

from agenttrace.models import BatchSpanRequest, SpanEvent, TraceContext


class TestSpanEvent:
    """Tests for SpanEvent model."""

    def test_create_with_defaults(self) -> None:
        """SpanEvent should auto-generate IDs and timestamps."""
        event = SpanEvent(agent_name="test_agent", event_type="llm_call")
        assert event.trace_id
        assert event.span_id
        assert event.agent_name == "test_agent"
        assert event.event_type == "llm_call"
        assert event.started_at is not None
        assert event.sdk_version == "0.1.0"

    def test_create_with_all_fields(self) -> None:
        """SpanEvent should accept all optional fields."""
        event = SpanEvent(
            trace_id="trace-123",
            span_id="span-456",
            parent_span_id="span-parent",
            agent_name="research_agent",
            event_type="llm_call",
            started_at=datetime.now(timezone.utc),
            ended_at=datetime.now(timezone.utc),
            latency_ms=150.5,
            model="gpt-4o",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            cost_usd=0.005,
            input_data={"prompt": "Hello"},
            output_data={"response": "Hi there"},
            error=None,
            metadata={"custom": "data"},
        )
        assert event.trace_id == "trace-123"
        assert event.model == "gpt-4o"
        assert event.cost_usd == 0.005

    def test_serialization_roundtrip(self) -> None:
        """SpanEvent should serialize and deserialize correctly."""
        event = SpanEvent(
            agent_name="test",
            event_type="tool_call",
            model="gpt-4o",
            prompt_tokens=100,
        )
        json_str = event.model_dump_json()
        restored = SpanEvent.model_validate_json(json_str)
        assert restored.agent_name == "test"
        assert restored.model == "gpt-4o"
        assert restored.prompt_tokens == 100

    def test_event_types(self) -> None:
        """All valid event types should be accepted."""
        valid_types = [
            "agent_start", "agent_end", "llm_call",
            "tool_call", "tool_end", "message", "error",
        ]
        for etype in valid_types:
            event = SpanEvent(agent_name="test", event_type=etype)
            assert event.event_type == etype


class TestBatchSpanRequest:
    """Tests for BatchSpanRequest model."""

    def test_batch_with_spans(self) -> None:
        """BatchSpanRequest should hold multiple spans."""
        spans = [
            SpanEvent(agent_name="a1", event_type="llm_call"),
            SpanEvent(agent_name="a2", event_type="tool_call"),
        ]
        batch = BatchSpanRequest(spans=spans)
        assert len(batch.spans) == 2

    def test_batch_serialization(self) -> None:
        """BatchSpanRequest should serialize correctly."""
        batch = BatchSpanRequest(
            spans=[SpanEvent(agent_name="test", event_type="llm_call")],
            agent_session_id="session-abc",
        )
        json_str = batch.model_dump_json()
        restored = BatchSpanRequest.model_validate_json(json_str)
        assert len(restored.spans) == 1
        assert restored.agent_session_id == "session-abc"


class TestTraceContext:
    """Tests for TraceContext model."""

    def test_create(self) -> None:
        """TraceContext should store trace propagation data."""
        ctx = TraceContext(
            trace_id="trace-1",
            parent_span_id="span-1",
            agent_name="agent-1",
        )
        assert ctx.trace_id == "trace-1"
        assert ctx.parent_span_id == "span-1"
        assert ctx.agent_name == "agent-1"

    def test_optional_parent(self) -> None:
        """parent_span_id should be optional."""
        ctx = TraceContext(trace_id="trace-1", agent_name="agent-1")
        assert ctx.parent_span_id is None
