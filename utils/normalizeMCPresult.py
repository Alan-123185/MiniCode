from typing import Any

from mcp_types import TextContent

from core.toolResult import toolResult



def normalize_MCP_result(result:Any,tool_name:str) -> toolResult:
    """
    归一化 MCP 结果，统一返回 toolResult 对象
    """
    if isinstance(result, toolResult):
        return result
    else:
        text_content: TextContent=[l for l in result if l["type"]=="text"][0]
        text=text_content.text
        text_lines=text.splitlines(keepends=False)
        result_lines=[]
        for line in text_lines:
            if line=="Partial failures: request_budget:budget_exhausted":
                continue
            result_lines.append(line)
        text="\n".join(result_lines)
        return toolResult(
            success=True,
            content=text,
            tool_name=tool_name
        )
