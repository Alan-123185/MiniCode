import json
import uuid
from typing import List
from langchain_core.messages import SystemMessage, BaseMessage, ToolMessage, AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from config.data import settings
from config.dependencies import get_db
from config.modelConfig import model_config
from exceptions import BizException
from mapper.summaryMapper import summaryMapper
from mappercommon.summary import Summary
from nodes.toolNode import tools
from states.OverallState import OverAllState
from utils.MessageTool import count_tokens



db = get_db()
summary_mapper=summaryMapper(db)
async def llm_node(state: OverAllState,config:RunnableConfig) -> OverAllState:
    input_message = pre_call_func(state,config)
    # 型是运行时选择的,必须调用时取最新,不能在模块级绑定
    model = model_config["value"]
    if model is None:
        raise BizException(message="---------ERROR 请先选择模型----------")
    system_prompt=config["configurable"]["system_prompt"].format(history_summary=state.summary_state)
    #提示词得改一下
    response =await model.bind_tools(tools).ainvoke([SystemMessage(content=system_prompt)]+input_message)
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
    tokens = count_tokens(windows_message)
    if tokens>settings.LLM_MAX_UP_MESSAGE_TOKEN:
        windows_message = degrade_windows(windows_message,tokens,config)
    return windows_message




def degrade_windows(messages:List[BaseMessage],all_tokens:int,config:RunnableConfig) -> List[BaseMessage]:
    """
    当消息过长时，尝试降级窗口内的消息，保留最新的对话和系统提示
    """
    # 1. 保留最新的对话
    latest_messages = []
    tokens=0
    msg_len=len(messages)
    for i in range(0,msg_len):
        msg = messages[i]
        if all_tokens-settings.LLM_MAX_UNDEGREDED_MESSAGE_TOKEN>tokens:
            tokens+=count_tokens([msg])
            latest_messages.append(compress_message(msg,config["thread_id"]))
        elif isinstance(msg, AIMessage) and  msg.tool_calls or isinstance(msg, ToolMessage):
            latest_messages.append(compress_message(msg,config["thread_id"]))
        else:
            new_tokens=count_tokens(latest_messages)
            if new_tokens+settings.LLM_MAX_UNDEGREDED_MESSAGE_TOKEN>settings.LLM_MAX_UP_MESSAGE_TOKEN:
                  while i<msg_len:
                        if isinstance(msg, ToolMessage):
                            latest_messages.append(compress_message(msg,config["thread_id"]))
                        else:
                            latest_messages.append(msg)
                        i+=1
            return latest_messages
    return latest_messages




def compress_message(msg:BaseMessage,session_id:str) -> BaseMessage:
    ret=msg
    if isinstance(msg, ToolMessage):
        tool_result = json.loads(msg.content)
        ret=ToolMessage(
            content=(tool_result["message"] or tool_result["error"] or tool_result["content"][:100]+"\n[此条工具调用已经降级，如需查看完整结果，请调用get_original_content工具函数传入tool_call_id:"+msg.tool_call_id+"]"),
            tool_call_id=msg.tool_call_id,
            name=tool_result["tool_name"]
        )
        summary_mapper.add_Tool_summary(Summary(
            session_id=session_id,
            tool_call_id=msg.tool_call_id,
            content=msg.content,
            compressed_content=ret.content,
            message_type=settings.LLM_MESSAGE_TYPE_TOOL,
        ))
    elif isinstance(msg, AIMessage):
        ret=AIMessage(
            content=f"{msg.content[:100]}...\n[此条ai回复已经降级，如需查看完整结果，请调用get_original_content_by_compressed_content工具函数传入memory_id:"+msg.additional_kwargs["memory_id"]+"]",
            tool_calls=msg["tool_calls"]
        )
        summary_mapper.add_LLM_summary(Summary(
            session_id=session_id,
            memory_id=msg.additional_kwargs["memory_id"],
            content=msg.content,
            compressed_content=ret.content,
            message_type=settings.LLM_MESSAGE_TYPE_AI,
        ))
        #先暂时不对用户消息降级
    return ret
