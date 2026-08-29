from langgraph.constants import END

from states.OverallState import OverAllState


def tool_condition_node(state: OverAllState) -> str:
    # if state["tool_call_count"] > settings.MAX_TOOL_CALLS:
    #     return END  # 硬性收场,不再给 LLM 机会
    return "tools" if state["messages"][-1].tool_calls else END

