"""Example: Tracing CrewAI agents with AgentTrace.

Prerequisites:
    pip install agenttrace crewai

Make sure the AgentTrace collector is running on http://localhost:8000.
"""

from agenttrace import tracer
from agenttrace.integrations.crewai import patch_crewai

# 1. Initialize AgentTrace
tracer.init(collector_url="http://localhost:8000")

# 2. Patch CrewAI (1 line — all Agent.execute_task calls are traced)
patch_crewai()

# 3. Use CrewAI normally
# from crewai import Agent, Task, Crew
#
# researcher = Agent(
#     role="Researcher",
#     goal="Find information about AI trends",
#     backstory="You are an expert AI researcher.",
# )
#
# task = Task(
#     description="Research the latest developments in AI agents.",
#     agent=researcher,
# )
#
# crew = Crew(agents=[researcher], tasks=[task])
# result = crew.kickoff()
# print(result)

print("CrewAI integration ready. Uncomment the code above to run.")
print("View traces at http://localhost:3000/traces")
