from pydantic import BaseModel


class decisionRequst(BaseModel):
    decision:str
    session_id:str