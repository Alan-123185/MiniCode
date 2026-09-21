from pydantic import BaseModel


class commandResult(BaseModel):
    success: bool
    stdout: str | None = None
    stderr: str | None = None
    exitcode: int