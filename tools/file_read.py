from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from config.data import settings
from core.toolResult import toolResult
from utils.MessageTool import compress_error
from utils.filePathTools import relativePathToAbsolute



@tool
def readfile(file_path: str,config:RunnableConfig) -> toolResult:
    """
    读取单个文本文件的内容。自带行号显示，方便精准定位代码缺陷。
    务必使用此工具查看代码内容！
    1. 如果之前的工具调用已经返回了目标文件路径，
    后续需要读取该文件时，直接使用该路径调用 readfile。

    2. 应充分利用之前的工具调用结果作为后续工具调用的参数。

    3. 当用户使用“刚才的文件”“这个文件”“上一个结果”等指代时，
    优先从历史工具结果中寻找对应的文件路径。

    :param file_path: 文件相对路径，请务必使用相对路径
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
    content = None
    used_encoding = None
    for enc in encodings_to_try:
        try:
            with open(target_path, 'r', encoding=enc) as f:
                content = f.read()
                used_encoding = enc
                lines = content.splitlines()
                numbered_lines = []
                for i, line in enumerate(lines):
                    numbered_lines.append(f"{i + 1:4d}| {line}")
                content= "\n".join(numbered_lines)
                break
        except UnicodeDecodeError:
            continue
        except Exception:
            # 其他异常（如权限）直接跳出循环，稍后统一处理
            continue

    if content is None:
        # 所有编码都失败，可能是二进制文件或权限问题
        # 最后尝试以二进制读取并忽略错误（但会丢失可读性），这里我们选择报错
        return toolResult(
            success=False,
            content="",
            error=f"无法用常见编码读取文件（{', '.join(encodings_to_try)}），文件可能是二进制或编码不兼容",
            tool_name="readfile"
        )

    return toolResult(
        success=True,
        message=f"读取文件{file_path}的结果,使用编码: {used_encoding}",
        content=content,
        tool_name="readfile"
    )


@tool
def listfiles(config:RunnableConfig,folder_path: str = ".") -> toolResult:
    """
    浏览某一个文件夹下的文件结构，只返回第一层（不递归）。

    1. 不要在已经获得明确文件路径的情况下重复调用 listfiles，
    除非路径失效或存在歧义。

    :param folder_path: 文件夹相对路径，请务必使用相对路径，默认为'.'，表示当前工作目录
    :return: 返回一个工具调用结果类
    """
    try:
        target_path =relativePathToAbsolute(folder_path,config)
    except Exception as e:
        return toolResult(
            success=False,
            content="",
            error=f"命令执行失败：{compress_error(str(e))}。请检查参数或跳过此步骤，建议如实告知用户",
            tool_name="listfiles"
        )

    if not target_path.exists():
        return toolResult(
            success=False,
            content="",
            error=f"目录不存在: {target_path}",
            tool_name="listfiles"
        )

    if not target_path.is_dir():
        return toolResult(
            success=False,
            content="",
            error=f"路径不是目录: {target_path}",
            tool_name="listfiles"
        )

    try:
        # 分别收集子目录和文件，并排序（不区分大小写，更友好）
        dirs = []
        files = []
        for entry in target_path.iterdir():
            # 跳过隐藏文件（可选），如果你想保留，可以删除这个判断
            if entry.name.startswith('.'):
                continue
            if entry.is_dir():
                dirs.append(entry.name)
            else:
                files.append(entry.name)

        dirs.sort(key=lambda x: x.lower())
        files.sort(key=lambda x: x.lower())

        # 构建清晰的内容字符串，保留你原有的格式
        content_parts = [
            f"当前目录 {folder_path} 下：",
            f"子文件夹: {', '.join(dirs) if dirs else '无'}",
            f"文件: {', '.join(files) if files else '无'}"
        ]
        content = "\n".join(content_parts)

        return toolResult(
            success=True,
            message=f"目录{folder_path}下的文件结构",
            content=content,
            tool_name="listfiles"
        )

    except PermissionError:
        return toolResult(
            success=False,
            content="",
            error=f"没有权限读取目录: {target_path}",
            tool_name="listfiles"
        )

    except Exception as e:
        return toolResult(
            success=False,
            content="",
            error=f"命令执行失败：{compress_error(str(e))}。请检查参数或跳过此步骤，建议如实告知用户",
            tool_name="listfiles"
        )



