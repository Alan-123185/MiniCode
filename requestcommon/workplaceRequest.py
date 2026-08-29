from pydantic import BaseModel


class WorksplaceRequest(BaseModel):
    workplace: str
    user_id: str
    session_id: str
