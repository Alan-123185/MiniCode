from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.constants import END
from loguru import logger
from config.data import settings
from prompt.aseembler import build_static_system_prompt, build_history_summary_prompt
from states.OverallState import OverAllState
from utils.MessageTool import count_tokens


def summerize_condition_node(state:OverAllState) -> str:
    # 条件1：消息总数超过最大条
    # 条件2：总token数超过限制
    # 满足任一条件即触发摘要
    system_prompt = build_static_system_prompt()
    history_summary_prompt=build_history_summary_prompt(state)
    system_message=[]
    if history_summary_prompt:
        system_message = [SystemMessage(content=system_prompt),HumanMessage(content=history_summary_prompt)]
    messages = state.messages or []
    messages = messages[state.last_summary_pos or 0:]
    if len(messages) <= 3:
        return END
    token_count=count_tokens(messages+system_message)
    if token_count>settings.LLM_MAX_TOKEN :
        logger.info(f"消息总数: {len(messages)}, 总token数: {token_count}, 超过限制，触发摘要")
        return "summerize"
    return END

