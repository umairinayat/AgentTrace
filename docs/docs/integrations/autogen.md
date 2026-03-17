# AutoGen Integration

AgentTrace integrates with Microsoft's AutoGen by patching `ConversableAgent.generate_reply`.

## Setup

```bash
pip install agenttrace pyautogen
```

## Usage

```python
from agenttrace import tracer
from agenttrace.integrations.autogen import patch_autogen

tracer.init(collector_url="http://localhost:8000")
patch_autogen()

# Your existing AutoGen code — unchanged
assistant = AssistantAgent("assistant", llm_config=llm_config)
user_proxy = UserProxyAgent("user_proxy")
user_proxy.initiate_chat(assistant, message="Hello")
```

## What Gets Traced

Each `generate_reply` call creates a span with:

- Agent name
- Input messages (last message summary)
- Reply output
- Execution time
- Errors (if any)

## How It Works

`patch_autogen()` monkey-patches `ConversableAgent.generate_reply`. The patch is idempotent.
