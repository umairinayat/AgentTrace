# LangChain Integration

AgentTrace integrates with LangChain via a callback handler that captures LLM calls and tool executions automatically.

## Setup

```bash
pip install agenttrace langchain langchain-openai
```

## Usage

```python
from agenttrace import tracer
from agenttrace.integrations.langchain import AgentTraceCallback

tracer.init(collector_url="http://localhost:8000")
callback = AgentTraceCallback(agent_name="research_agent")

# Use with any LangChain chain
chain = LLMChain(llm=llm, prompt=prompt, callbacks=[callback])
result = chain.run("What is the capital of France?")
```

## What Gets Traced

| Event | Captured Data |
|-------|---------------|
| LLM calls | Model name, prompt, response, tokens, cost, latency |
| Tool calls | Tool input, output, latency |
| Errors | Error message, stack trace |

## Configuration

```python
callback = AgentTraceCallback(
    agent_name="my_agent",    # Name shown in dashboard
    trace_id="custom-id",     # Optional: set a custom trace ID
)
```

## How It Works

The `AgentTraceCallback` implements LangChain's callback interface:

- `on_llm_start` / `on_llm_end` — Captures LLM call timing and token usage
- `on_tool_start` / `on_tool_end` — Captures tool execution
- `on_llm_error` / `on_tool_error` — Captures errors with timing

Each event is sent asynchronously to the collector via the SDK's batched event queue.
