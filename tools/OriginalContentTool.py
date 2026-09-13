from langchain_core.tools import tool
from core.toolResult import toolResult
from service.summaryService import summaryService

summary_service=summaryService()
@tool
def get_original_content_by_tool_call_id(tool_call_id: str) -> toolResult:
    """
    获取原始内容，主要用于在摘要后，大模型需要查看某一条被降级的工具调用消息的完整原始内容时使用
    @param tool_call_id: 工具调用的id
    @return: 返回原始内容字符串
    """
    summary = summary_service.get_content_by_tool_call_id(tool_call_id)
    if not summary:
        return toolResult(
            success=False,
            content="",
            error=f"未找到对应的 summary，tool_call_id: {tool_call_id},请检查tool_call_id是否正确。",
            tool_name="get_original_content_by_tool_call_id"
        )
    else:
        return toolResult(
            success=True,
            message=f"获取tool_call_id为{tool_call_id}的工具消息的原始内容",
            content=summary["content"],
            error="",
            tool_name="get_original_content_by_tool_call_id"
        )



@tool
def get_original_content_by_compressed_content(memory_id: str) -> toolResult:
    """
    这个工具可以根据压缩内容获取原始内容，适合在摘要后，大模型需要查看某一条被降级的消息的完整原始内容时使用
    @param compressed_content: 压缩内容
    @param session_id: 会话ID
    @return: 返回原始内容
    """
    summary = summary_service.get_content_by_compressed_content(memory_id)
    if not summary:
        return toolResult(
            success=False,
            content="",
            error=f"未找到对应的 summary ,请检查compressed_content是否正确。",
            tool_name="get_original_content_by_compressed_content"
        )
    return toolResult(
        success=True,
        message="获取原始内容",
        content=summary["content"],
        error="",
        tool_name="get_original_content_by_compressed_content"
    )
