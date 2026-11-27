from pathlib import Path
from typing import TypedDict

from pydantic import BaseModel


class CallRequest(BaseModel):
    message: str
    session_id:str
    path:str

class problemInfo(BaseModel):
    instance_id:str
    repo:str
    base_commit:str
    problem_statement:str


class resultInfo(TypedDict):
    instance_id:str
    model_name_or_path:str
    model_patch:str
