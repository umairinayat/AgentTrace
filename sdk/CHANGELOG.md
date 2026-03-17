# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0] - 2026-03-17

### Added
- Core `Tracer` class with singleton pattern
- `@trace_agent` decorator for sync and async functions
- Context manager `tracer.span()` API
- Async event queue with batched flushing
- Local JSONL fallback buffer when collector is unreachable
- Cost estimation via `pricing.json`
- LangChain integration (`AgentTraceCallback`)
- LangGraph integration (`patch_langgraph`)
- CrewAI integration (`patch_crewai`)
- AutoGen integration (`patch_autogen`)
- OpenAI SDK integration (`patch_openai`)
- Ollama integration (`traced_ollama_client`)
- Context propagation via `contextvars`
- Pydantic v2 models for `SpanEvent`, `BatchSpanRequest`, `TraceContext`
