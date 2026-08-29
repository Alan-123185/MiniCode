import time
from pydantic import BaseModel, Field


class OperationGroup(BaseModel):
    group_id: str
    session_id: str
    user_prompt:str
    created_at:int = Field(default_factory=lambda: int(time.time()))
    is_undone: bool=False
