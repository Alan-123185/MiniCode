import time
from typing import Optional

from pydantic import BaseModel, Field

from sandbox_executor.MXCExecutor import MxcExecutor


class Session(BaseModel):
    session_id : str
    session_name : Optional[str]="新会话"
    workplace  : Optional[str]=None
    user_id    : str
    create_time : int=Field(default_factory=lambda: int(time.time()))

