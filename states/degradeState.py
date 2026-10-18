from langchain_core.messages import BaseMessage
from pydantic import BaseModel

from states.OverallState import OverAllState


class degradeState(OverAllState):
    """
    降级状态，记录降级后的消息内容和其他数据
    """

    degraded_messages: list[BaseMessage] = []
