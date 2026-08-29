from typing import Optional, Literal

from pydantic import BaseModel

from config.data import Settings, settings
from core.AgentResult import AgentResult
from core.toolStatusEvent import toolstatusEvent


class InterruptResult(BaseModel):
    message: toolstatusEvent | str | None = None
    agentResult: Optional[AgentResult]= None
    type: Literal[settings.interrupt_type_approve, settings.interrupt_type_info,settings.interrupt_type_result]