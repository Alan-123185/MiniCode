from pydantic import BaseModel


class InputState(BaseModel):
    input: str