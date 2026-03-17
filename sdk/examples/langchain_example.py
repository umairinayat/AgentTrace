"""Example: Tracing a LangChain chain with AgentTrace.

Prerequisites:
    pip install agenttrace langchain langchain-openai

Make sure the AgentTrace collector is running on http://localhost:8000.
"""

from agenttrace import tracer
from agenttrace.integrations.langchain import AgentTraceCallback

# 1. Initialize AgentTrace (2 lines — that's it)
tracer.init(collector_url="http://localhost:8000")

# 2. Create the callback
callback = AgentTraceCallback(agent_name="research_agent")

# 3. Use it with any LangChain chain
# from langchain_openai import ChatOpenAI
# from langchain.chains import LLMChain
# from langchain.prompts import PromptTemplate
#
# llm = ChatOpenAI(model="gpt-4o-mini")
# prompt = PromptTemplate.from_template("Summarize: {topic}")
# chain = LLMChain(llm=llm, prompt=prompt, callbacks=[callback])
# result = chain.run("the history of artificial intelligence")
# print(result)

print("LangChain integration ready. Uncomment the code above to run.")
print("View traces at http://localhost:3000/traces")
