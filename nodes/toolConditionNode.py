from langgraph.constants import END
from loguru import logger

from config.data import settings
from states.OverallState import OverAllState


def tool_condition_node(state: OverAllState) -> str:
    # if state.tool_call_count > settings.MAX_TOOL_CALLS:
    #     return END  # 当连续无进度工具调用次数超过阈值时，直接结束对话
    logger.info(f"判断是否需要调用工具: {state.messages[-1].tool_calls}")
    return "tools" if state.messages[-1].tool_calls else END

