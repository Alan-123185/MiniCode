from typing import Any
from core.toolResult import toolResult


def normalize_MCP_result(result: Any, tool_name: str) -> toolResult:
    """
    归一化 MCP 结果，统一返回 toolResult 对象
    """
    if isinstance(result, toolResult):
        return result

    # 1. 先把结果统一转成文本
    if isinstance(result, str):
        text = result

    elif isinstance(result, list):
        text_parts = []
        skipped = 0

        for block in result:
            # 兼容 dict：{"type": "text", "text": "..."}
            if isinstance(block, dict):
                block_type = block.get("type")
                if block_type == "text":
                    text_parts.append(block.get("text", ""))
                else:
                    skipped += 1
            else:
                # 兼容对象：TextContent(type="text", text="...")
                block_type = getattr(block, "type", None)
                if block_type == "text":
                    text_parts.append(getattr(block, "text", ""))
                else:
                    skipped += 1

        if text_parts:
            text = "\n".join(text_parts)
            if skipped:
                text += f"\n[已跳过 {skipped} 个非文本内容块]"
        elif skipped:
            text = f"[未找到文本内容，已跳过 {skipped} 个非文本内容块]"
        else:
            text = "[工具返回了空内容]"

    else:
        # 可能是 ToolMessage / Command 之类的对象，尝试取 content
        content = getattr(result, "content", None)
        if content is not None:
            return normalize_MCP_result(content, tool_name)

        # 实在不认识就转字符串兜底
        text = str(result)

    # 2. 保留你原来的过滤逻辑
    text_lines = text.splitlines(keepends=False)
    result_lines = []
    for line in text_lines:
        if line == "Partial failures: request_budget:budget_exhausted":
            continue
        result_lines.append(line)
    text = "\n".join(result_lines)

    return toolResult(
        success=True,
        content=text,
        tool_name=tool_name
    )