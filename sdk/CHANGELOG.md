# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Fixed
- The local JSONL fallback buffer is now actually drained. `flush_local_buffer()`
  was never called, so spans written while the collector was down stayed on disk
  permanently. Spilled spans are replayed on the next successful send and at
  interpreter exit, including spills left behind by a previous process.
- `TraceClient.send_batch()` raises on transport failure instead of swallowing the
  error and returning 0, which had made the queue's retry path unreachable.
  Retry policy now lives solely in `EventQueue`.
- The flusher drains the whole buffer each cycle instead of one batch, removing a
  `batch_size / flush_interval` throughput ceiling (5 events/sec at defaults) that
  caused events to be dropped under load.
- Event buffering is thread-safe. The `asyncio.Queue` was replaced with a
  lock-guarded `deque`, since integrations emit spans from framework worker
  threads and the queue was also bound to a single event loop.
- `flush_sync()` and `tracer.flush()` no longer risk spinning forever when the
  collector is unreachable.

### Added
- Exponential backoff (capped at 60s) between failed flush attempts.
- Spans are spilled to disk after `max_retries` consecutive failures rather than
  being retried in memory indefinitely.
- `max_queue_size` and `max_retries` options on `tracer.init()`.
- `buffer_dir` option on `TraceClient` so the spill path can be isolated.
- The spill file is capped at 64 MiB, and dropped events are counted
  (`EventQueue.dropped_count`) rather than only logged.

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
