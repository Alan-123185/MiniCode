from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.constants import END
from loguru import logger
from config.data import settings
from prompt.aseembler import build_static_system_prompt, build_history_summary_prompt
from states.OverallState import OverAllState
from utils.MessageTool import count_tokens


def degrade_condition_node(state: OverAllState):
    """
    判断是否需要降级处理
    条件1：消息总数超过最大条
    条件2：总token数超过限制
    满足任一条件即触发降级处理
    """
    system_message=[]
    system_prompt = build_static_system_prompt()
    history_summary_prompt = build_history_summary_prompt(state)
    if history_summary_prompt:
        system_message = [SystemMessage(content=system_prompt), HumanMessage(content=history_summary_prompt)]
    messages = state.messages or []
    messages = messages[state.last_summary_pos or 0:]
    if len(messages) <= 3:
        return END
    token_count = count_tokens(system_message+messages)
    if token_count > settings.LLM_MAX_TOKEN:
        logger.info(f"消息总数: {len(messages)}, 总token数: {token_count}, 超过限制，触发降级处理")
        return "degrade"