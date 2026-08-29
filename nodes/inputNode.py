from langchain_core.messages import HumanMessage, SystemMessage

from config.data import Settings, settings
from states.InputState import InputState
from states.OverallState import OverAllState


def input_node(state: InputState) -> OverAllState:
    result = {
        "messages": [HumanMessage(content=state["input"])],
        "steps": [f"analyze user question: {state['input']}......"],
        "input": state["input"]
    }
    return result