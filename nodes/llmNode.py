import uuid
from typing import List
from langchain_core.messages import SystemMessage, BaseMessage, ToolMessage, AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from loguru import logger
from config.data import settings
from config.modelConfig import model_config
from exceptions import BizException
from mappercommon.summary import Summary
from service.summaryService import summaryService
from states.OverallState import OverAllState
from tools.toolManage import tools
from utils.MessageTool import count_tokens
from utils.compressMessage import _forced_compress_tool_result

summary_service=summaryService()
async def llm_node(state: OverAllState,config:RunnableConfig) -> OverAllState:
    input_message = pre_call_func(state,config)
    logger.info(input_message)
    # 型是运行时选择的,必须调用时取最新,不能在模块级绑定
    model = model_config["value"]
    if model is None:
        raise BizException(message="ERROR 请先选择模型")
    system_prompt=config["configurable"]["system_prompt"].format(history_summary=state.summary_state)
    #提示词得改一下
    response = None
    try:
        async for chunk in model.bind_tools(tools).astream([SystemMessage(content=system_prompt)]+input_message):
            response = chunk if response is None else response + chunk
    except Exception as e:
        raise BizException(message=f"ERROR 生成失败")
    # 1. 生成 message_id
    message_id =str(uuid.uuid4()).replace("-", "")
    # 2. 把 message_id 塞进 additional_kwargs
    if response.additional_kwargs is None:
        response.additional_kwargs = {}
    response.additional_kwargs["memory_id"] = message_id
    usage = response.usage_metadata
    logger.info("respnse:"+str(response))
    return {
        "output": response.content,
        "messages": [response],
        "total_tokens": usage["total_tokens"] if usage else 0,
        "steps": ["thinking......"]
    }




def pre_call_func(state: OverAllState,config:RunnableConfig) -> List[BaseMessage]:
    # 先把窗口内消息拿出来
    windows_message = state.messages[state.last_summary_pos:]
    """
    10.2 我决定放开豁免最新的用户消息的限制，统一处理，无论是否最新
    """
    current_message=[]
    for i in range(len(windows_message) - 1, -1, -1):
        if isinstance(windows_message[i], HumanMessage):
            current_message = windows_message[i:]   #这一部分消息是最新的用户消息，必须保留
            windows_message = windows_message[:i]   #这一部分消息是窗口内的历史消息，可能需要降级
            break
    windows_tokens = count_tokens(windows_message)
    current_tokens = count_tokens(current_message)
    all_tokens=windows_tokens+current_tokens
    delta_tokens = all_tokens - settings.LLM_MAX_UP_MESSAGE_TOKEN
    #如果超过了最大限制，先降级窗口内的消息，再降级当前消息
    if delta_tokens>0:
        windows_message, delta_tokens = degrade_windows_l1(windows_message, delta_tokens, config)
    if delta_tokens>0:
        current_message, delta_tokens = degrade_windows_l1(current_message, delta_tokens, config)
    if delta_tokens>0:
        windows_message , delta_tokens = degrade_windows_l2(windows_message, delta_tokens)
    if delta_tokens>0:
        current_message , delta_tokens = degrade_windows_l2(current_message, delta_tokens)
    return windows_message+current_message





def degrade_windows_l1(messages:List[BaseMessage],delta_tokens,config:RunnableConfig) -> tuple[List[BaseMessage],int] :
    """
    当消息过长时，尝试降级窗口内的消息，保留最新的对话和系统提示，
    这里先这样处理，每次都单独处理一次窗口内消息，后面再来优化
    """
    # 1. 保留最新的对话
    if not messages:
        return [],delta_tokens
    latest_messages = []
    msg_len=len(messages)
    for i in range(0,msg_len):
        msg = messages[i]
        if delta_tokens>0:
            old_tokens=count_tokens([msg])
            new_msg=compress_message(msg,config.get("configurable", {}).get("thread_id"))
            latest_messages.append(new_msg)
            new_tokens=count_tokens([new_msg])
            delta_tokens=delta_tokens-(old_tokens-new_tokens)
        elif isinstance(msg, AIMessage) and  msg.tool_calls or isinstance(msg, ToolMessage):
            latest_messages.append(compress_message(msg,config.get("configurable", {}).get("thread_id")))
        else:
            return latest_messages+messages[i:],delta_tokens
    return latest_messages,delta_tokens


#二次降级，针对工具调用结果和AI回复的降级，为了节约成本选择丢失更多信息
def degrade_windows_l2(messages:List[BaseMessage],delta_tokens) -> tuple[List[BaseMessage],int] :
    if not messages:
        return [],delta_tokens
    msg_len=len(messages)
    ret=[]
    for i in range(0,msg_len):
        msg = messages[i]
        ret.append(msg)
        if isinstance(msg, AIMessage):
            j=i+1
            while j<msg_len and isinstance(messages[j] ,ToolMessage) :
                if delta_tokens > 0:
                    content=_forced_compress_tool_result(messages[j].tool_call_id)
                    ret.append(ToolMessage(content=content,tool_call_id=messages[j].tool_call_id,name=messages[j].name))
                    old_tokens=count_tokens([messages[j]])
                    delta_tokens=delta_tokens-old_tokens
                    j += 1
                else:
                    ret.extend(messages[j:])
                    return ret,delta_tokens
            i=j-1
    return ret,delta_tokens





"""
9.27 分层消息降级，杜绝字符粗暴截断 丢失细节的自然语言摘要
"""
def compress_message(msg:BaseMessage,session_id:str) -> BaseMessage:
    ret=msg
    if isinstance(msg, ToolMessage):
        summary = summary_service.query_tool_summary(tool_call_id=msg.tool_call_id)
        if summary:
            ret=ToolMessage(
                content=summary["compressed_content"],
                tool_call_id=msg.tool_call_id,
                name=msg.name
            )
        else:
            snippet = (msg.content or "")[:100]  # 要么是content，要么是error，至少有一个不为空
            content = f"{snippet}\n [system Info]工具结果已降级，tool_call_id:{msg.tool_call_id}]"
            ret=ToolMessage(
                content=content,
                tool_call_id=msg.tool_call_id,
                name=msg.name
            )
            summary_service.add_Tool_summary(Summary(
                session_id=session_id,
                tool_call_id=msg.tool_call_id,
                content=msg.content,
                compressed_content=ret.content,
                message_type=settings.LLM_MESSAGE_TYPE_TOOL,
            ))
    elif isinstance(msg, AIMessage):
        summary = summary_service.query_LLM_summary(memory_id=msg.additional_kwargs["memory_id"])
        if summary:
            ret=AIMessage(
                content=summary["compressed_content"],
                tool_calls=msg.tool_calls
            )
        else:
            ret=AIMessage(
                content=f"{msg.content[:100]}...\n[----system message----此条ai回复已经降级，memory_id:"+msg.additional_kwargs["memory_id"]+"]",
                tool_calls=msg.tool_calls
            )
            summary_service.add_LLM_summary(Summary(
                session_id=session_id,
                memory_id=msg.additional_kwargs["memory_id"],
                content=msg.content,
                compressed_content=ret.content,
                message_type=settings.LLM_MESSAGE_TYPE_AI,
            ))
        #先暂时不对用户消息降级
    return ret




