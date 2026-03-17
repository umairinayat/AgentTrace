# AgentTrace

**See exactly what your agents are doing — every step, every decision, every cost.**

AgentTrace is a fully open-source, self-hosted observability and debugging platform for multi-agent AI systems. It captures every LLM call, tool execution, sub-agent message, token cost, and latency — and correlates them into a visual trace timeline.

## Key Features

- **Zero-config SDK** — 2 lines to start tracing
- **Visual trace timeline** — D3.js Gantt chart showing every span
- **Cost tracking** — Per-call and per-trace cost analytics
- **Behavioral drift detection** — Detects when model providers silently change behavior
- **Framework integrations** — LangChain, LangGraph, CrewAI, AutoGen, Ollama
- **Fully self-hosted** — MIT licensed, your data stays on your infrastructure

## Quick Example

```python
from agenttrace import tracer

tracer.init(collector_url="http://localhost:8000")

@tracer.trace_agent(name="my_agent")
async def my_agent(query: str) -> str:
    return await llm.ainvoke(query)
```

## Architecture

```
SDK (pip install agenttrace)
    |
    v  HTTP/JSON
Collector (FastAPI)  <-->  Dashboard (React)
    |
    v
Drift Detector (sentence-transformers)
```

## Getting Started

See the [Installation](installation.md) and [Quickstart](quickstart.md) guides.
