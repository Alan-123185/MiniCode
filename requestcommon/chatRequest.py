from typing import Literal, Optional

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    user_id: str = "user_local"
    session_id: str
