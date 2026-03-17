"""Example: Tracing a LangGraph workflow with AgentTrace.

Prerequisites:
    pip install agenttrace langgraph langchain-openai

Make sure the AgentTrace collector is running on http://localhost:8000.
"""

from agenttrace import tracer
from agenttrace.integrations.langgraph import patch_langgraph

# 1. Initialize AgentTrace
tracer.init(collector_url="http://localhost:8000")

# 2. Patch LangGraph (1 line — all StateGraph nodes are traced)
patch_langgraph()

# 3. Use LangGraph normally
# from langgraph.graph import StateGraph
# from typing import TypedDict
#
# class AgentState(TypedDict):
#     query: str
#     result: str
#
# def researcher(state: AgentState) -> AgentState:
#     return {"query": state["query"], "result": "researched: " + state["query"]}
#
# def writer(state: AgentState) -> AgentState:
#     return {"query": state["query"], "result": "written: " + state["result"]}
#
# graph = StateGraph(AgentState)
# graph.add_node("researcher", researcher)
# graph.add_node("writer", writer)
# graph.set_entry_point("researcher")
# graph.add_edge("researcher", "writer")
# graph.set_finish_point("writer")
#
# app = graph.compile()
# result = app.invoke({"query": "AI safety", "result": ""})
# print(result)

print("LangGraph integration ready. Uncomment the code above to run.")
print("View traces at http://localhost:3000/traces")
