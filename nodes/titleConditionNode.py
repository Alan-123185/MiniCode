from langchain_core.runnables import RunnableConfig
from langgraph.types import Send

from config.dependencies import get_session
from states.OverallState import OverAllState


def title_condition_node(state:OverAllState,config:RunnableConfig) -> list[Send]:
    sends=[Send["output_node",{}]]
    if  get_session(config).session_name == "新会话" :
        sends.append(Send["title_node",{}])
    return sends
