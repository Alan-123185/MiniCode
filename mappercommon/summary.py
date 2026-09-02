from datetime import datetime
from typing import Optional, Literal

from pydantic import BaseModel, ConfigDict, Field

from config.data import settings


class Summary(BaseModel):
    session_id: str
    # 消息基础信息
    message_type: str = Literal[settings.LLM_MESSAGE_TYPE_SYSTEM, settings.LLM_MESSAGE_TYPE_HUMAN, settings.LLM_MESSAGE_TYPE_AI, settings.LLM_MESSAGE_TYPE_TOOL]
    content: Optional[str] = None
    compressed_content: Optional[str] = None
    # 工具调用相关
    tool_call_id: Optional[str] = None
    # 扩展字段
    additional_kwargs: Optional[str] = None  # JSON 字符串
