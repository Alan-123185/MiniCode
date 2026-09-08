from pydantic import BaseModel
from core.AgentResult import AgentResult

class OutputState(BaseModel):
    agentResult: AgentResult