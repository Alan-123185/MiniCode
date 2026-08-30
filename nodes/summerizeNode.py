from langchain_core.messages import SystemMessage
from config.modelConfig import model_config
from exceptions import BizException
from nodes.toolNode import tools
from prompt.summerize_prompt import SUMMERIZE_PROMPT
from states.OverallState import OverAllState
from utils.MessageTool import trim_message, trim_old_messages


def summerize_node(state:OverAllState) -> OverAllState:
    """
    当会话长度到一定程度时，总结窗口外的内容，减少上下文长度
    """
    model=model_config["value"]
    if not model :
        raise BizException(message="---------ERROR 请先选择模型----------")

    pos=trim_message(state["messages"])   #滑动窗口历史左边界，右侧是若干条完整对话
    all_message = state["messages"]
    last_summary_pos=state.get("last_summary_pos",0)  #把上一次摘要的位置传进来
    llm_message=all_message[pos:]          #窗口内对话历史
    message = all_message[last_summary_pos:(pos-1)]    #需要进行摘要的是上次摘要到的有边界到滑动窗口的左边界
    summerize_prompt=SUMMERIZE_PROMPT.format(old_summary=state["summary"],conversation_history=trim_old_messages(message))

    res = model.bind_tools(tools).invoke(SystemMessage(content=summerize_prompt))

    return {
        "summary":res,
        "messages":state["messages"],
        "windows_message":llm_message,
        "last_summary_pos":pos
    }





