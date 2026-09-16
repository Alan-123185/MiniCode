from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from config.data import settings
from core.toolResult import toolResult
from utils.MessageTool import compress_error
from utils.filePathTools import relativePathToAbsolute



@tool
def readfile(
    config: RunnableConfig ,
    file_path: str,
    start_line: int | None = None,
    end_line: int | None = None,

) -> toolResult:
    """
    读取单个文本文件的内容，返回原始文件内容（不含行号前缀）。
    务必使用此工具查看代码内容！
    1. 如果之前的工具调用已经返回了目标文件路径，
    后续需要读取该文件时，直接使用该路径调用 readfile。
    2. 应充分利用之前的工具调用结果作为后续工具调用的参数。
    3. 如果文件过大，系统会自动截断输出，并提示使用 `start_line` 和 `end_line` 参数来读取指定行范围。
    :param file_path: 文件相对路径，请务必使用相对路径
    :param start_line: 可选，起始行号，从 1 开始计数。只传它时不传 end_line，表示读取从该行到文件末尾的内容
    :param end_line: 可选，结束行号，从 1 开始计数，包含该行。只传它时不传 start_line，表示读取从第 1 行到该行的内容
    :return: 返回一个工具调用结果类
    """
    try:
        target_path =relativePathToAbsolute(file_path,config)
    except Exception as e:
        return toolResult(
            success=False,
            content="",
            error=f"命令执行失败：{compress_error(str(e))}。请检查参数或跳过此步骤，建议如实告知用户",
            tool_name="readfile"
        )

    # 先检查文件是否存在且是普通文件
    if not target_path.exists():
        return toolResult(
            success=False,
            content="",
            error=f"文件不存在: {target_path}",
            tool_name="readfile"
        )
    if not target_path.is_file():
        return toolResult(
            success=False,
            content="",
            error=f"路径指向的不是一个普通文件: {target_path}",
            tool_name="readfile"
        )

    # 尝试用多种常见编码读取，避免因编码问题崩溃
    encodings_to_try = settings.ENCODINGS_TO_TRY
    raw_content = None
    used_encoding = None
    for enc in encodings_to_try:
        try:
            with open(target_path, 'r', encoding=enc) as f:
                raw_content = f.read()
                used_encoding = enc
                break
        except UnicodeDecodeError:
            continue
        except Exception:
            # 其他异常（如权限）直接跳出循环，稍后统一处理
            continue

    if raw_content is None:
        # 所有编码都失败，可能是二进制文件或权限问题
        # 最后尝试以二进制读取并忽略错误（但会丢失可读性），这里我们选择报错
        return toolResult(
            success=False,
            content="",
            error=f"无法用常见编码读取文件（{', '.join(encodings_to_try)}），文件可能是二进制或编码不兼容",
            tool_name="readfile"
        )

    lines = raw_content.splitlines()
    total_lines = len(lines)
    if len(raw_content) > settings.READ_FILE_MAX_COUNT and start_line is None and end_line is None:
        head = raw_content[:settings.RETURN_FILE_MAX_COUNT]
        tail = raw_content[-settings.RETURN_FILE_MAX_COUNT:]
        return toolResult(
            success=False,
            content=f"[system Info] 文件过大({len(raw_content)/1024:.2f}KB)， 共 {total_lines} 行)。\n"
            "为防止上下文爆炸，系统仅展示【前1000个字符】和【后1000个字符】的内容。\n"
            "如果需要查找特定内容，请停止使用 readfile，改用 `search_file_by_keyword` 或者命令行工具 \n"
            "如果需要读取中间部分或者需要完整的格式信息，请重新调用readfile并传入 `start_line` 和 `end_line` \n"
            "--- 以下是文件头部 ---\n"
            f"{head}\n"
            "--- 以下是文件尾部 ---\n"
            f"{tail}",
            tool_name="readfile"
        )


    # ---------- 解析可选的行范围参数 ----------
    if start_line is None and end_line is None:
        # 未传行号参数，读取全部内容（保持原有行为）
        real_start = 0
        real_end = total_lines
        range_desc = f"全部内容(共{total_lines}行)"
    else:
        # 参数合法性校验
        if (start_line is not None and start_line < 1) or (end_line is not None and end_line < 1):
            return toolResult(
                success=False,
                content="",
                error=f"start_line/end_line 必须从 1 开始计数，收到: start_line={start_line}, end_line={end_line}",
                tool_name="readfile"
            )
        if start_line is not None and end_line is not None and start_line > end_line:
            return toolResult(
                success=False,
                content="",
                error=f"start_line({start_line}) 不能大于 end_line({end_line})，文件共 {total_lines} 行",
                tool_name="readfile"
            )
        if start_line is not None and start_line > total_lines:
            return toolResult(
                success=False,
                content="",
                error=f"start_line({start_line}) 超出文件总行数({total_lines})，请检查行号后重试",
                tool_name="readfile"
            )

        # 归一化为 0-based 左闭右开区间；end_line 超出总行数时宽容截断到文件末尾
        real_start = (start_line if start_line is not None else 1) - 1
        real_end = min(end_line, total_lines) if end_line is not None else total_lines
        range_desc = f"第{real_start + 1}行到第{real_end}行(共{real_end - real_start}行)"

    # ---------- 直接返回原文（不加行号；读取范围已在 message 中说明） ----------
    content = "\n".join(lines[real_start:real_end])

    return toolResult(
        success=True,
        message=f"读取文件{file_path}的结果({range_desc}),使用编码: {used_encoding}",
        content=content,
        tool_name="readfile"
    )



class ListFilesInput(BaseModel):
    folder_path:str=Field(default=".",description="文件夹相对路径，默认'.'表示工作区根目录")
    depth:int=Field(default=1, ge=1, description="递归深度，默认为 1；1 表示仅显示当前目录下一层")


#listfiles工具增强 目录树
@tool(args_schema=ListFilesInput)
def listfiles(config:RunnableConfig,folder_path: str = ".",depth:int =1 ) -> toolResult:
    """
    以目录树形式浏览某个文件夹（支持按 depth 递归展开）。
    输出采用 tree 风格（如 ├── / └── / │），目录优先、名称不区分大小写排序，
    并默认跳过以 "." 开头的隐藏文件和目录。
    """
    try:
        target_path =relativePathToAbsolute(folder_path,config)
    except Exception as e:
        return toolResult(
            success=False,
            error=f"命令执行失败：{compress_error(str(e))}。请检查参数或跳过此步骤，建议如实告知用户",
            tool_name="listfiles"
        )

    if not target_path.exists():
        return toolResult(
            success=False,
            error=f"目录不存在: {target_path}",
            tool_name="listfiles"
        )

    if not target_path.is_dir():
        return toolResult(
            success=False,
            error=f"路径不是目录: {target_path}",
            tool_name="listfiles"
        )

    try:
        if depth < 1:
            return toolResult(
                success=False,
                error=f"depth 必须大于等于 1，收到: {depth}",
                tool_name="listfiles"
            )

        def build_tree(current_path, current_depth: int, prefix: str = "") -> list[str]:
            lines: list[str] = []
            entries = [e for e in current_path.iterdir() if not e.name.startswith('.')]
            entries.sort(key=lambda e: (not e.is_dir(), e.name.lower()))

            for index, entry in enumerate(entries):
                is_last = index == len(entries) - 1
                branch = "└── " if is_last else "├── "
                lines.append(f"{prefix}{branch}{entry.name}")

                if entry.is_dir() and current_depth < depth:
                    child_prefix = f"{prefix}{'    ' if is_last else '│   '}"
                    lines.extend(build_tree(entry, current_depth + 1, child_prefix))

            return lines

        tree_lines = [f"{folder_path}"]
        tree_lines.extend(build_tree(target_path, 1))
        content = "\n".join(tree_lines)

        return toolResult(
            success=True,
            message=f"浏览目录{folder_path}下的目录树结构（depth={depth}）",
            content=content,
            tool_name="listfiles"
        )

    except PermissionError:
        return toolResult(
            success=False,
            error=f"没有权限读取目录: {target_path}",
            tool_name="listfiles"
        )

    except Exception as e:
        return toolResult(
            success=False,
            error=f"命令执行失败：{compress_error(str(e))}。请检查参数或跳过此步骤，建议如实告知用户",
            tool_name="listfiles"
        )

