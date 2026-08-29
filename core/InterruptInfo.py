from typing import List

from pydantic import BaseModel


class InterruptInfo(BaseModel):
    tool_name: str
    tool_args: dict
    message: str

