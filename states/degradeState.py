from langchain_core.messages import BaseMessage
from pydantic import BaseModel


class degradeState(BaseModel):
    """
    降级状态，记录降级后的消息内容和其他数据
    """
    degraded_messages: list[BaseMessage] = []
