"""AgentTrace framework integrations.

Each integration provides zero- or minimal-config tracing for popular
AI agent frameworks. Import the specific integration you need:

    from agenttrace.integrations.langchain import AgentTraceCallback
    from agenttrace.integrations.langgraph import patch_langgraph
    from agenttrace.integrations.crewai import patch_crewai
    from agenttrace.integrations.autogen import patch_autogen
    from agenttrace.integrations.openai_sdk import patch_openai
    from agenttrace.integrations.openai_api import traced_openai_client
    from agenttrace.integrations.openai_agents import patch_openai_agents
    from agenttrace.integrations.ollama import traced_ollama_client
"""

__all__ = [
    "langchain",
    "langgraph",
    "crewai",
    "autogen",
    "openai_sdk",
    "openai_api",
    "openai_agents",
    "ollama",
]
