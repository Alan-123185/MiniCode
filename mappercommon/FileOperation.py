import time
from typing import Optional, Literal

from pydantic import BaseModel, Field

from config.data import settings


class FileOperation(BaseModel):
    """Represents a row from the `file_operations` table."""

    group_id: str
    file_path: str
    operation_type: Literal[*settings.file_change_tool_list]
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    old_snippet: Optional[str] = None
    new_snippet: Optional[str] = None
    created_at: int = Field(default_factory=lambda: int(time.time()))
