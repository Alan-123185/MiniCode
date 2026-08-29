from core.AgentResult import AgentResult
from states.OverallState import OverAllState
from states.outputState import OutputState


def output_node(state: OverAllState) -> OutputState:
    return {
        "agentResult":
        AgentResult(
            answer= state["messages"][-1].content,
            total_tokens= state["total_tokens"],
            steps= state["steps"],
            status= "success"
        )
    }
