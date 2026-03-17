"""Tests for the LangChain integration callback."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

from agenttrace.integrations.langchain import AgentTraceCallback


class TestAgentTraceCallback:
    """Test LangChain callback handler."""

    def test_init_defaults(self) -> None:
        """Should create callback with default agent name."""
        cb = AgentTraceCallback()
        assert cb.agent_name == "langchain_agent"
        assert cb.trace_id is not None

    def test_init_custom(self) -> None:
        """Should accept custom agent name and trace ID."""
        cb = AgentTraceCallback(agent_name="my_agent", trace_id="custom-id")
        assert cb.agent_name == "my_agent"
        assert cb.trace_id == "custom-id"

    def test_on_llm_start_records_span(self) -> None:
        """on_llm_start should record timing and prompt."""
        cb = AgentTraceCallback(agent_name="test")
        run_id = uuid.uuid4()

        cb.on_llm_start(
            serialized={"kwargs": {"model_name": "gpt-4o"}},
            prompts=["Hello world"],
            run_id=run_id,
        )

        span_id = str(run_id)
        assert span_id in cb._span_starts
        assert cb._span_prompts[span_id] == "Hello world"
        assert cb._span_models[span_id] == "gpt-4o"

    @patch("agenttrace.integrations.langchain.AgentTraceCallback._get_tracer")
    def test_on_llm_end_emits_event(self, mock_get_tracer: MagicMock) -> None:
        """on_llm_end should emit a SpanEvent."""
        mock_tracer = MagicMock()
        mock_get_tracer.return_value = mock_tracer

        cb = AgentTraceCallback(agent_name="test")
        run_id = uuid.uuid4()

        cb.on_llm_start(
            serialized={"kwargs": {"model_name": "gpt-4o"}},
            prompts=["Hello"],
            run_id=run_id,
        )

        # Simulate response
        response = MagicMock()
        response.llm_output = {"token_usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}}
        response.generations = [[MagicMock(text="World")]]

        cb.on_llm_end(response=response, run_id=run_id)

        mock_tracer._emit.assert_called_once()
        event = mock_tracer._emit.call_args[0][0]
        assert event.agent_name == "test"
        assert event.event_type == "llm_call"
        assert event.prompt_tokens == 10
        assert event.completion_tokens == 20

    @patch("agenttrace.integrations.langchain.AgentTraceCallback._get_tracer")
    def test_on_tool_end_emits_event(self, mock_get_tracer: MagicMock) -> None:
        """on_tool_end should emit a tool span event."""
        mock_tracer = MagicMock()
        mock_get_tracer.return_value = mock_tracer

        cb = AgentTraceCallback(agent_name="test")
        run_id = uuid.uuid4()

        cb.on_tool_start(serialized={}, input_str="search query", run_id=run_id)
        cb.on_tool_end(output="search results", run_id=run_id)

        mock_tracer._emit.assert_called_once()
        event = mock_tracer._emit.call_args[0][0]
        assert event.event_type == "tool_end"
