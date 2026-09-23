from langgraph.constants import END
from loguru import logger
from config.data import settings
from states.OverallState import OverAllState
from utils.MessageTool import count_tokens


def summerize_condition_node(state:OverAllState) -> str:
    # 条件1：消息总数超过最大条
    # 条件2：总token数超过限制
    # 满足任一条件即触发摘要
    messages = state.messages or []
    messages = messages[state.last_summary_pos or 0:]
    if len(messages) <= 3:
        return END
    token_count=count_tokens(messages)
    if token_count>settings.LLM_MAX_TOKEN :
        logger.info(f"消息总数: {len(messages)}, 总token数: {token_count}, 超过限制，触发摘要")
        return "summerize"
    return END

