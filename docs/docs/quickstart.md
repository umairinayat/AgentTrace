# Quickstart

Get traces flowing in under 5 minutes.

## 1. Start the Collector

```bash
docker compose up -d
```

## 2. Install the SDK

```bash
pip install agenttrace
```

## 3. Add 2 Lines to Your Code

```python
from agenttrace import tracer

tracer.init(collector_url="http://localhost:8000")
```

That's it. Now use the decorator or context manager to trace your agents:

### Using the Decorator

```python
@tracer.trace_agent(name="summarizer")
async def summarize(text: str) -> str:
    return await llm.ainvoke(f"Summarize: {text}")
```

### Using the Context Manager

```python
async def my_agent(query: str):
    with tracer.span("my_agent", agent_name="custom_agent") as span:
        span.set_input({"query": query})
        response = await call_my_llm(query)
        span.set_output({"response": response})
        return response
```

### Using Framework Integrations

=== "LangChain"

    ```python
    from agenttrace.integrations.langchain import AgentTraceCallback

    callback = AgentTraceCallback(agent_name="my_agent")
    chain = LLMChain(llm=llm, prompt=prompt, callbacks=[callback])
    ```

=== "LangGraph"

    ```python
    from agenttrace.integrations.langgraph import patch_langgraph

    patch_langgraph()
    # All StateGraph nodes are now traced automatically
    ```

=== "CrewAI"

    ```python
    from agenttrace.integrations.crewai import patch_crewai

    patch_crewai()
    # All Agent.execute_task calls are now traced
    ```

=== "Ollama"

    ```python
    from agenttrace.integrations.ollama import traced_ollama_client

    client = traced_ollama_client()
    response = client.post("/api/chat", json={...})
    ```

## 4. View Your Traces

Open the dashboard at [http://localhost:3000](http://localhost:3000).

You'll see:

- **Trace List** — All captured traces with duration, tokens, cost
- **Trace Detail** — Gantt timeline of every span in a trace
- **Cost Analytics** — Token spend by agent and model
- **Drift Monitor** — Behavioral drift detection alerts
