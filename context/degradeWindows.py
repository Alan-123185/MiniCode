from langchain_core.messages import BaseMessage, AIMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from context.compressMessage import compress_message
from service.summaryService import summaryService
from utils.MessageTool import count_tokens
from utils.compressResult import forced_compress_tool_result




summary_service=summaryService()



def degrade_windows_l1(messages:list[BaseMessage],delta_tokens,config:RunnableConfig) -> tuple[list[BaseMessage],int] :
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
            new_msg=compress_message(msg,config.get("configurable", {}).get("thread_id"),summary_service)
            latest_messages.append(new_msg)
            new_tokens=count_tokens([new_msg])
            delta_tokens=delta_tokens-(old_tokens-new_tokens)
        else:
            return latest_messages+messages[i:],delta_tokens
    return latest_messages,delta_tokens





#二次降级，针对工具调用结果和AI回复的降级，为了节约成本选择丢失更多信息
def degrade_windows_l2(messages:list[BaseMessage],delta_tokens) -> tuple[list[BaseMessage],int] :
    if not messages:
        return [],delta_tokens
    msg_len=len(messages)
    ret=[]
    i=0
    while i < msg_len:
        msg = messages[i]
        ret.append(msg)
        if isinstance(msg, AIMessage):
            j=i+1
            while j<msg_len and isinstance(messages[j] ,ToolMessage) :
                if delta_tokens > 0:
                    content=forced_compress_tool_result(messages[j].tool_call_id)
                    ret.append(ToolMessage(content=content if content else messages[j].content,tool_call_id=messages[j].tool_call_id,name=messages[j].name))
                    old_tokens=count_tokens([messages[j]])
                    delta_tokens=delta_tokens-old_tokens
                    j += 1
                else:
                    ret.extend(messages[j:])
                    return ret,delta_tokens
            i=j
        else:
            i += 1
    return ret,delta_tokens

