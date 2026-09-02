from pydantic import BaseModel
from typing import Optional, Annotated, List
from langgraph.graph.message import add_messages
from langgraph.managed import RemainingSteps
import operator
from states.SummaryState import summaryState


# 自定义合并字典的 Reducer
def merge_dicts(a: dict, b: dict) -> dict:
    return {**a, **b}



def merge_delta(old_state: summaryState, delta: summaryState) -> summaryState:
    """把增量合并到全局状态，追加 + 去重 + 冲突处理"""

    old_state.modified_files += delta.modified_files
    old_state.modified_files=list(set(old_state.modified_files))
    old_state.key_interfaces += delta.key_interfaces
    old_state.key_interfaces=list(set(old_state.key_interfaces))
    old_state.environment_notes += delta.environment_notes
    old_state.environment_notes=list(set(old_state.environment_notes))
    old_state.pending_issues += delta.pending_issues
    old_state.pending_issues=list(set(old_state.pending_issues))
    old_state.pending_issues=[issue for issue in old_state.pending_issues if issue not in delta.completed_milestones]
    old_state.completed_milestones += delta.completed_milestones
    old_state.completed_milestones=list(set(old_state.completed_milestones))

    return old_state

class OverAllState(BaseModel):  # 注意这里继承 BaseModel
    # 继承 messages 需要手动写出来（或继承 MessagesState 但用 Pydantic 重写）
    messages: Annotated[list, add_messages] = []  # 手动实现 MessagesState 功能

    input: str = ""  # 给默认空串，防止 KeyError
    remaining_steps: RemainingSteps  # 这个由 LangGraph 自动注入，不需要默认值

    # 累加器
    steps: Annotated[list[str], operator.add] = []
    total_tokens: Annotated[int, operator.add] = 0

    # 结果字段
    agentResult: Optional[dict] = None  # 如果有 AgentResult 类型，正常导入即可

    # 统计字段 - 使用自定义 Reducer 合并
    tool_call_count: Annotated[dict[str, int], merge_dicts] = {}

    # 摘要与窗口（只保留一份消息，不再冗余）
    summaryState : Annotated[summaryState,merge_delta] = summaryState()
    last_summary_pos: int = 0  # 游标，用默认覆盖即可
