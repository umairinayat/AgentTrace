# Ollama Integration

AgentTrace traces Ollama API calls via a custom httpx transport wrapper.

## Setup

```bash
pip install agenttrace
# Ollama must be running: ollama serve
```

## Usage

```python
from agenttrace import tracer
from agenttrace.integrations.ollama import traced_ollama_client

tracer.init(collector_url="http://localhost:8000")
client = traced_ollama_client(base_url="http://localhost:11434")

response = client.post("/api/chat", json={
    "model": "llama3.2",
    "messages": [{"role": "user", "content": "Hello!"}],
    "stream": False,
})
```

## What Gets Traced

Each `/api/chat` or `/api/generate` call creates a span with:

- Model name
- Prompt text
- Response text
- Token counts (eval_count, prompt_eval_count)
- Estimated cost
- Latency
- Errors (if any)

## Configuration

```python
client = traced_ollama_client(
    base_url="http://my-ollama-server:11434",
    timeout=60.0,
)
```

## How It Works

`traced_ollama_client()` returns an httpx.Client with a custom transport that intercepts requests to Ollama's chat and generate endpoints. Non-Ollama requests pass through unmodified.
