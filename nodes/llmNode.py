from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig
from config.modelConfig import model_config
from exceptions import BizException
from nodes.toolNode import tools
from states.OverallState import OverAllState
from utils.MessageTool import trim_message


async def llm_node(state: OverAllState,config:RunnableConfig) -> OverAllState:
    windows_msg = state.get("windows_message", [])
    if windows_msg:  # 如果列表不为空
        input_message = windows_msg
    else:
        input_message = state["messages"][trim_message(state["messages"]):]
    # 型是运行时选择的,必须调用时取最新,不能在模块级绑定
    model = model_config["value"]
    if model is None:
        raise BizException(message="---------ERROR 请先选择模型----------")
    system_prompt=config["configurable"]["system_prompt"].format(history_summary=state.get("summary",""))
    response =await model.bind_tools(tools).ainvoke([SystemMessage(content=system_prompt)]+input_message)
    usage = response.usage_metadata
    return {
        "output": response.content,
        "messages": [response],
        "total_tokens": usage["total_tokens"] if usage else 0,
        "steps": ["thinking......"]
    }
