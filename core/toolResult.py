from pydantic import BaseModel
from typing import Any

class toolResult(BaseModel):

    success: bool=True
    #工具作用提示
    message: str = ""

    # 返回给LLM看的内容 str类型
    content: str=""

    # 机器处理的数据
    data: Any = None

    # 错误信息
    error: str | None = None

    # 工具名称
    tool_name: str | None = None

def toolResultToText(toolresult: toolResult) -> str:
    """
    将 toolResult 对象转换为文本格式，便于在日志或输出中查看。
    """
    data = toolresult.model_dump()  # 变成字典
    success = data.get("success", False)
    content = data.get("content") or ""
    message = data.get("message") or ""
    error = data.get("error") or ""

    if success:
        return f"message: {message}\n--- content ---\n{content}\n"
    else:
        return f"message: {message}\n--- error ---\n{error}\n"


def textTotoolResult(text: str) -> toolResult:
    """
    将文本转换为 toolResult 对象。

    支持两种格式：
    1. toolResultToText() 生成的文本格式
    2. JSON 格式字符串
    """

    text = text.strip()
    if not text:
        logger.error("输入文本为空，无法转换为 toolResult 对象。")
        return toolResult(success=False, message="输入文本为空，无法转换为 toolResult 对象。")

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = None

    if isinstance(parsed, dict):
        try:
            return toolResult(**parsed)
        except Exception:
            logger.error("解析 JSON 数据时出错。")
            raise BizException(message="解析 JSON 数据时出错。")

    message = ""
    content = ""
    error = ""
    success = True
    current_section = None

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line:
            continue

        stripped = line.strip()

        if stripped == "--- content ---":
            current_section = "content"
            continue

        if stripped == "--- error ---":
            current_section = "error"
            success = False
            continue

        if current_section is None:
            if stripped.startswith("success:"):
                value = stripped[len("success:") :].strip().lower()
                if value == "false":
                    success = False
                elif value == "true":
                    success = True
                continue

            if stripped.startswith("message:"):
                message = stripped[len("message:") :].strip()
                continue

            if stripped.startswith("error:"):
                error = stripped[len("error:") :].strip()
                success = False
                continue

            continue

        if current_section == "content":
            content += (line + "\n")
        elif current_section == "error":
            error += (line + "\n")

    if error:
        success = False

    return toolResult(
        success=success,
        message=message,
        content=content.rstrip("\n"),
        error=error.rstrip("\n") or None,
    )