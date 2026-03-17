# CrewAI Integration

AgentTrace integrates with CrewAI by patching `Agent.execute_task` to capture task execution spans.

## Setup

```bash
pip install agenttrace crewai
```

## Usage

```python
from agenttrace import tracer
from agenttrace.integrations.crewai import patch_crewai

tracer.init(collector_url="http://localhost:8000")
patch_crewai()

# Your existing CrewAI code — unchanged
crew = Crew(agents=[researcher, writer], tasks=[task1, task2])
result = crew.kickoff()
```

## What Gets Traced

Each `Agent.execute_task` call creates a span with:

- Agent role as agent name
- Task description as input
- Task result as output
- Execution time
- Errors (if any)

## How It Works

`patch_crewai()` monkey-patches `Agent.execute_task`. The patch is idempotent.
