from pydantic import BaseModel


class editMessageRequest(BaseModel):
    message_id: str
    new_content: str
    session_id:str