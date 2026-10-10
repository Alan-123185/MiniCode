from functools import lru_cache

from langchain_core.runnables import RunnableConfig
from context.pipline import pre_call_func
from states.OverallState import OverAllState
from loguru import logger
# 全局缓存，用于存储已处理的 summary

def degrade_node(state: OverAllState, config: RunnableConfig) -> dict:
    """
    降级节点，主要用于在消息过多时，降低消息的token数量
    """
    degraded_messages = pre_call_func(state, config)
    logger.info(f"降级后的消息: {degraded_messages}")
    return {
        "degraded_messages": degraded_messages
    }