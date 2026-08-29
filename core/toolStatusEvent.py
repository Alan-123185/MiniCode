from typing import Literal, Optional

from pydantic import BaseModel

from config.data import Settings, settings
from core.toolResult import toolResult


class toolstatusEvent(BaseModel):
    status: Literal[settings.tool_failed,settings.tool_success,settings.tool_try,settings.tool_refused]
    tool_name: str
    args: Optional[dict]=None
    result: Optional[toolResult]=None
    user_prompt: Optional[str]=None