from langgraph.graph import MessagesState
from core.AgentResult import AgentResult

class OutputState(MessagesState):
    agentResult: AgentResult