from langchain_core.tools import tool

from states.OverallState import OverAllState


@tool
def record_fact(fact: str,state:OverAllState):
    """
    记录事实的工具函数。
    用于帮助agent记录事实，确保在后续的对话中可以引用这些事实。
    """

