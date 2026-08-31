from langchain_core.messages import SystemMessage
from config.modelConfig import model_config
from exceptions import BizException
from prompt.summerize_prompt import SUMMERIZE_PROMPT
from states.OverallState import OverAllState
from states.SummaryState import summaryState
from utils.MessageTool import trim_message, trim_old_messages


async def summerize_node(state:OverAllState) -> OverAllState:
    """
    当会话长度到一定程度时，总结窗口外的内容，减少上下文长度
    """
    model=model_config["value"]
    if not model :
        raise BizException(message="---------ERROR 请先选择模型----------")
    all_message = state["messages"]
    pos=trim_message(all_message)               #滑动窗口历史左边界，右侧是若干条完整对话
    last_summary_pos=state.get("last_summary_pos",0)  #把上一次摘要的位置传进来
    llm_message=all_message[pos:]                     #窗口内对话历史
    message = all_message[last_summary_pos:pos]   #需要进行摘要的是上次摘要到的有边界到滑动窗口的左边界
    summerize_prompt=SUMMERIZE_PROMPT.format(old_summary=state["summary"],conversation_history=trim_old_messages(message))
    #这里改一下提示词
    summarystate = await model.with_structured_output(summaryState).ainvoke(SystemMessage(content=summerize_prompt))

    return {
        "summaryState":summarystate,
        "messages":state["messages"],
        "last_summary_pos":pos
    }





