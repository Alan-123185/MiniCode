from langchain_core.messages import SystemMessage, BaseMessage
from loguru import logger
from config.data import settings
from config.dependencies import create_no_streaming_model
from config.modelConfig import model_config
from exceptions import BizException
from prompt.summerize_prompt import SUMMERIZE_PROMPT
from states.OverallState import OverAllState
from utils.MessageTool import trim_message


async def summerize_node(state: OverAllState) -> OverAllState:
    """
    当会话长度到一定程度时，总结窗口外的内容，减少上下文长度
    """
    model = model_config["value"]
    if not model:
        raise BizException(message="ERROR 请先选择模型")
    all_message = state.messages
    pos = trim_message(all_message)  # 滑动窗口历史左边界，右侧是若干条完整对话
    last_summary_pos = state.last_summary_pos or 0  # 把上一次摘要的位置传进来
    llm_message = all_message[pos:]  # 窗口内对话历史
    message = all_message[last_summary_pos:pos]  # 需要进行摘要的是上次摘要到的有边界到滑动窗口的左边界
    old_summary = state.summary_state

    summerize_prompt = SUMMERIZE_PROMPT.format(
        old_summary=old_summary, conversation_history=_trim_old_messages(message)
    )
    # 这里改一下提示词

    model = create_no_streaming_model(model)
    response = await model.ainvoke(
        [SystemMessage(content=summerize_prompt)], reasoning_effort="none", extra_body={"enable_thinking": False}
    )
    new_summary = str(response.content).strip()
    summary_state = new_summary if new_summary else old_summary  # 防止模型返回空值
    logger.info(f"summary_state: {summary_state}")
    return {"summary_state": summary_state, "last_summary_pos": pos}


def _trim_old_messages(messages: list[BaseMessage]) -> str:
    cleaned_history = []
    for msg in messages:
        if len(msg.content) > settings.MAX_OLD_MESSAGE_LENGTH:
            content = msg.content[: settings.MAX_OLD_MESSAGE_LENGTH] + "...该条消息太长，已截断"
        else:
            content = msg.content
        cleaned_history.append(f"{msg.type}:{content}")
    return "\n".join(cleaned_history)
