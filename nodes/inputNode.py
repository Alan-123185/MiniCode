from langchain_core.messages import HumanMessage
from loguru import logger

from states.InputState import InputState
from states.OverallState import OverAllState


def input_node(state: InputState) -> OverAllState:
    result = {
        "messages": [HumanMessage(content=state.input)],
        "steps": [f"analyze user question: {state.input}......"],
        "input": state.input,
    }
    logger.info(f"输入内容: {state.input}")
    return result
