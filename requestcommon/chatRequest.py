from pydantic import BaseModel


class ChatRequest(BaseModel):
    message :str
    user_id : str
    session_id : str