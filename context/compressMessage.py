
"""
9.27 分层消息降级，杜绝字符粗暴截断 丢失细节的自然语言摘要
"""
from langchain_core.messages import BaseMessage, ToolMessage, AIMessage

from config.data import settings
from mappercommon.summary import Summary
from service.summaryService import summaryService






"""
第一级处理，减去低价值对话
"""
def snip_message(msgs:list[BaseMessage]) -> list[BaseMessage]:
    msg_len=len(msgs)
    i=0
    while i < msg_len:
        msg=msgs[i]
        if isinstance(msg, AIMessage) and msg.tool_calls:
            j = i + 1
            while j < msg_len and isinstance(msgs[j], ToolMessage):
                content=msgs[j].content
                if not content or "user refused tool" in content :
                    msg.tool_calls = [tc for tc in msg.tool_calls if tc["id"] != msgs[j].tool_call_id]
                    msgs.pop(j)
                    msg_len -= 1
                else:
                    j+=1
            if not msg.tool_calls:
                msgs.pop(i)
                msg_len -= 1
            else:
                i=j
        else:
            i+=1
    return msgs









def compress_message(msg:BaseMessage,session_id:str,summary_service:summaryService) -> BaseMessage:
    ret=msg
    #把已经过时的工具调用结果降级为提示信息
    if msg.additional_kwargs.get("outdated",False):
        return ToolMessage(
            content=f"{msg.content[:100]}...\n[system Info]由于文件被修改，此条工具调用已过时，如有需要建议重新读取文件或查看旧内容",
            tool_call_id=msg.tool_call_id,
            name=msg.name
        )

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
            content = f"{snippet}\n [system Info]工具结果已降级,需要可以调用 get_original_content_by_tool_call_id 获取完整结果"
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
                content=f"{msg.content[:100]}...\n[system Info]此条ai回复已经降级，如需查看完整内容，可以调用 get_original_content_by_memory_id 获取。memory_id:"+msg.additional_kwargs["memory_id"],
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