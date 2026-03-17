# OpenAI SDK Integration

AgentTrace integrates with the OpenAI Python SDK by patching `ChatCompletions.create` to capture every chat completion call.

## Setup

```bash
pip install agenttrace openai
```

## Usage

```python
from agenttrace import tracer
from agenttrace.integrations.openai_sdk import patch_openai

tracer.init(collector_url="http://localhost:8000")
patch_openai()

# Your existing OpenAI code — unchanged
import openai
client = openai.OpenAI()
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello!"}],
)
```

## What Gets Traced

Each `chat.completions.create` call creates a span with:

- Model name
- Prompt (last message content)
- Response text
- Token usage (prompt, completion, total)
- Estimated cost
- Latency
- Errors (if any)

## How It Works

`patch_openai()` monkey-patches `Completions.create` in the OpenAI SDK. The patch is idempotent — calling it multiple times has no effect. Non-chat API calls are not affected.
