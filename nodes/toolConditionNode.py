from langgraph.constants import END
from loguru import logger

from states.OverallState import OverAllState


def tool_condition_node(state: OverAllState) -> str:
    # if state.tool_call_count > settings.MAX_TOOL_CALLS:
    #     return END  # 硬性收场,不再给 LLM 机会
    logger.info(f"判断是否需要调用工具: {state.messages[-1].tool_calls}")
    return "tools" if state.messages[-1].tool_calls else END

