from langchain_core.runnables import RunnableConfig
from context.degradeManage.pipline import pre_call_func
from langchain_core.messages import SystemMessage, HumanMessage
from loguru import logger
from config.data import settings
from prompt.aseembler import build_static_system_prompt, build_history_summary_prompt
from states.OverallState import OverAllState
from utils.MessageTool import count_tokens

# 全局缓存，用于存储已处理的 summary


def degrade_node(state: OverAllState, config: RunnableConfig) -> dict:
    """
    降级节点，主要用于在消息过多时，降低消息的token数量
    """
    system_message = []
    system_prompt = build_static_system_prompt()
    history_summary_prompt = build_history_summary_prompt(state)
    if history_summary_prompt:
        system_message = [SystemMessage(content=system_prompt), HumanMessage(content=history_summary_prompt)]
    messages = state.messages or []
    messages = messages[state.last_summary_pos or 0 :]
    degraded_messages = system_message + messages
    if len(messages) <= 3:
        return {"degraded_messages": degraded_messages}
    token_count = count_tokens(system_message + messages)
    if token_count > settings.LLM_MAX_TOKEN:
        logger.info(f"消息总数: {len(messages)}, 总token数: {token_count}, 超过限制，触发降级处理")
        degraded_messages = pre_call_func(state, config)
        logger.info(f"降级后的消息: {degraded_messages}")
    return {"degraded_messages": degraded_messages}
