# AgentTrace SDK

Open-source observability SDK for multi-agent AI systems.

## Installation

```bash
pip install agenttrace
```

## Quick Start

```python
from agenttrace import tracer

tracer.init(collector_url="http://localhost:8000")

@tracer.trace_agent(name="my_agent")
async def my_agent(query: str) -> str:
    return await llm.invoke(query)
```

See the [main README](../README.md) for full documentation.
