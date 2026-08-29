from pydantic import BaseModel
from typing import Any

class toolResult(BaseModel):

    success: bool=True
    #工具作用提示
    message: str = ""

    # 返回给LLM看的内容 str类型
    content: str=""

    # 机器处理的数据
    data: Any = None

    # 错误信息
    error: str | None = None

    # 工具名称
    tool_name: str | None = None