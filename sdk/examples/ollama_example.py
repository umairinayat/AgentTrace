"""Example: Tracing Ollama LLM calls with AgentTrace.

Prerequisites:
    pip install agenttrace
    # Ollama must be running locally: ollama serve

Make sure the AgentTrace collector is running on http://localhost:8000.
"""

from agenttrace import tracer
from agenttrace.integrations.ollama import traced_ollama_client

# 1. Initialize AgentTrace
tracer.init(collector_url="http://localhost:8000")

# 2. Create a traced Ollama client
client = traced_ollama_client(base_url="http://localhost:11434")

# 3. Make LLM calls — they're automatically traced
# response = client.post("/api/chat", json={
#     "model": "llama3.2",
#     "messages": [
#         {"role": "user", "content": "Explain quantum computing in 3 sentences."}
#     ],
#     "stream": False,
# })
# print(response.json()["message"]["content"])

print("Ollama integration ready. Uncomment the code above to run.")
print("View traces at http://localhost:3000/traces")
