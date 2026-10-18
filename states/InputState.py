from typing import Literal

from pydantic import BaseModel


class InputState(BaseModel):
    input: str
    mode: Literal["work", "free_fly", "plan"] = "work"
