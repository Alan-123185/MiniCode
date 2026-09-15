from pydantic import BaseModel
from typing import Any, Optional


class toolResult(BaseModel):
    success: bool = True
    message: str = ""
    content: str = ""
    data: Any = None
    error: Optional[str] = None
    tool_name: Optional[str] = None
