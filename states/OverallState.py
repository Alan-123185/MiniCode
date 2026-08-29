
from langgraph.managed import RemainingSteps
from core.AgentResult import AgentResult
import operator
from typing import Annotated, Optional
from langgraph.graph import MessagesState
from langchain_core.messages import BaseMessage


class OverAllState(MessagesState):
    input: str
    remaining_steps: RemainingSteps

    # 累加器字段
    steps: Annotated[list[str], operator.add] = []
    total_tokens: Annotated[int, operator.add] = 0

    # 结果字段
    agentResult: Optional[AgentResult] = None

    # 统计字段（建议给个初始空字典，或者用自定义 reducer 合并）
    tool_call_count: dict = {}

    # 摘要与窗口
    summary: str = ""  # 给空字符串默认值
    windows_message: list[BaseMessage] = []  #  给空列表默认值

    # 游标字段
    last_summary_pos: int = 0  # 建议设为 0，而不是 None