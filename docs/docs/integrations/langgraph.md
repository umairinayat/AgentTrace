# LangGraph Integration

AgentTrace integrates with LangGraph by patching `StateGraph.add_node` to wrap every node function with tracing.

## Setup

```bash
pip install agenttrace langgraph langchain-openai
```

## Usage

```python
from agenttrace import tracer
from agenttrace.integrations.langgraph import patch_langgraph

tracer.init(collector_url="http://localhost:8000")
patch_langgraph()  # 1 line — patches all StateGraph instances

# Your existing LangGraph code — unchanged
graph = StateGraph(AgentState)
graph.add_node("researcher", researcher_node)
graph.add_node("writer", writer_node)
```

## What Gets Traced

Every node execution is captured as a span with:

- Node name as agent name
- Input state
- Output state
- Execution time
- Errors (if any)

## How It Works

`patch_langgraph()` monkey-patches `StateGraph.add_node` so that each node function is wrapped in a tracing context. The patch is idempotent — calling it multiple times has no effect.
