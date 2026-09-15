
import uuid
from typing import List
from langchain_core.messages import SystemMessage, BaseMessage, ToolMessage, AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from config.data import settings
from config.modelConfig import model_config
from exceptions import BizException
from mappercommon.summary import Summary
from nodes.toolNode import tools
from service.summaryService import summaryService
from states.OverallState import OverAllState
from utils.MessageTool import count_tokens

summary_service=summaryService()
async def llm_node(state: OverAllState,config:RunnableConfig) -> OverAllState:
    input_message = pre_call_func(state,config)
    # 型是运行时选择的,必须调用时取最新,不能在模块级绑定
    model = model_config["value"]
    if model is None:
        raise BizException(message="---------ERROR 请先选择模型----------")
    system_prompt=config["configurable"]["system_prompt"].format(history_summary=state.summary_state)
    #提示词得改一下
    response = None
    try:
        async for chunk in model.bind_tools(tools).astream([SystemMessage(content=system_prompt)]+input_message):
            response = chunk if response is None else response + chunk
    except Exception as e:
        raise BizException(message=f"---------ERROR 生成失败----------")
    # 1. 生成 message_id
    message_id = str(uuid.uuid4())
    # 2. 把 message_id 塞进 additional_kwargs
    if response.additional_kwargs is None:
        response.additional_kwargs = {}
    response.additional_kwargs["memory_id"] = message_id
    usage = response.usage_metadata
    return {
        "output": response.content,
        "messages": [response],
        "total_tokens": usage["total_tokens"] if usage else 0,
        "steps": ["thinking......"]
    }




def pre_call_func(state: OverAllState,config:RunnableConfig) -> List[BaseMessage]:
    # 先把窗口内消息拿出来
    windows_message = state.messages[state.last_summary_pos:]
    current_message=[]
    for i in range(len(windows_message) - 1, -1, -1):
        if isinstance(windows_message[i], HumanMessage):
            current_message = windows_message[i:]   #这一部分消息是最新的用户消息，必须保留
            windows_message = windows_message[:i]   #这一部分消息是窗口内的历史消息，可能需要降级
            break
    tokens = count_tokens(windows_message)
    if tokens>settings.LLM_MAX_UP_MESSAGE_TOKEN:
        windows_message = degrade_windows(windows_message,tokens,config)
    return windows_message+current_message




def degrade_windows(messages:List[BaseMessage],all_tokens:int,config:RunnableConfig) -> List[BaseMessage]:
    """
    当消息过长时，尝试降级窗口内的消息，保留最新的对话和系统提示，

    这里先这样处理，每次都单独处理一次窗口内消息，后面再来优化
    """
    # 1. 保留最新的对话
    if not messages:
        return []
    latest_messages = []
    tokens=0
    msg_len=len(messages)
    for i in range(0,msg_len):
        msg = messages[i]
        if all_tokens-settings.LLM_MAX_UNDEGREDED_MESSAGE_TOKEN>tokens:
            tokens+=count_tokens([msg])
            latest_messages.append(compress_message(msg,config.get("configurable", {}).get("thread_id")))
        elif isinstance(msg, AIMessage) and  msg.tool_calls or isinstance(msg, ToolMessage):
            latest_messages.append(compress_message(msg,config.get("configurable", {}).get("thread_id")))
        else:
            new_tokens=count_tokens(latest_messages)
            if new_tokens+settings.LLM_MAX_UNDEGREDED_MESSAGE_TOKEN>settings.LLM_MAX_UP_MESSAGE_TOKEN:
                  while i<msg_len:
                        if isinstance(messages[i], ToolMessage):
                            latest_messages.append(compress_message(messages[i],config.get("configurable", {}).get("thread_id")))
                        else:
                            latest_messages.append(messages[i])
                        i+=1
                  return latest_messages
            else:
                return latest_messages+messages[i:]
    return latest_messages




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
            snippet = (msg.content or "")[:100]  #要么是content，要么是error，至少有一个不为空
            content = f"{snippet}\n[----system Info----工具结果已截断，tool_call_id:{msg.tool_call_id}]"
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
