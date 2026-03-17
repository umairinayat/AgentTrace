<div align="center">
  <h1>AgentTrace</h1>
  <p>Open-source observability for multi-agent AI systems</p>

  ![PyPI](https://img.shields.io/pypi/v/agenttrace)
  ![License](https://img.shields.io/badge/license-MIT-blue)
  ![Tests](https://github.com/agenttrace/agenttrace/actions/workflows/ci.yml/badge.svg)
</div>

## The Problem

89% of developers think they have agent observability. Only 62% actually do.

When your agent breaks in production, can you answer:
- Which LLM call failed?
- What was the exact prompt that caused it?
- Which tool executed and what did it return?
- How much did that trace cost?
- Did your agent silently change behavior when OpenAI updated their model?

AgentTrace answers all of these.

## Quickstart (2 minutes)

```bash
# Start AgentTrace
docker compose up -d

# Install the SDK
pip install agenttrace
```

```python
from agenttrace import tracer
from agenttrace.integrations.langchain import AgentTraceCallback

tracer.init(collector_url="http://localhost:8000")
callback = AgentTraceCallback(agent_name="my_agent")

# Add callback to your existing LangChain code
chain = your_existing_chain.with_config(callbacks=[callback])
result = chain.invoke({"input": "your query"})
```

Open the dashboard at http://localhost:3000

## Features

- **Full trace visibility** -- every LLM call, tool execution, and sub-agent message
- **Behavioral drift detection** -- alerts when your agent changes behavior (unique to AgentTrace)
- **Cost tracking** -- token spend per trace, per agent, per model
- **Latency profiling** -- Gantt timeline shows exactly where time is spent
- **Self-hosted** -- your data never leaves your machine
- **Zero config** -- one `docker compose up`, two lines of Python

## Framework Support

| Framework | Status |
|---|---|
| LangChain | Supported |
| LangGraph | Supported |
| CrewAI | Supported |
| AutoGen | Supported |
| Ollama (local LLMs) | Supported |
| OpenAI Agents SDK | Supported |
| Custom agents | Manual span API |

## Architecture

AgentTrace consists of four components:

1. **Python SDK** (`pip install agenttrace`) -- lightweight decorators and callbacks
2. **Collector** (FastAPI) -- receives, stores, and serves trace data
3. **Drift Detector** -- background worker detecting behavioral changes
4. **Dashboard** (React + D3.js) -- visual trace timeline and analytics

## Installation

### Docker (recommended)
```bash
git clone https://github.com/agenttrace/agenttrace.git
cd agenttrace
docker compose up -d
pip install agenttrace
```

### From source
```bash
git clone https://github.com/agenttrace/agenttrace.git
cd agenttrace/sdk
pip install -e ".[dev]"
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT -- see [LICENSE](LICENSE) for details.
