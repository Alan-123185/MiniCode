import difflib
import os

from langchain_core.runnables import RunnableConfig

from config.data import settings
from core.toolResult import toolResult
from utils.MessageTool import compress_error
from utils.filePathTools import relativePathToAbsolute

encodings_to_try=settings.ENCODINGS_TO_TRY

def file_edit_tool(
    file_path: str,
    start_line: int,
    end_line: int,
    new_content: str,
    config:RunnableConfig
) -> toolResult:

    target_path =relativePathToAbsolute(file_path,config)
    if not os.path.exists(target_path):
        return toolResult(success=False, message=f"文件 '{target_path}' 不存在。如想增加文件请调用create_file工具",
                          content="")

    try:
        # 1. 自动检测编码(与 file_read 一致),写回时沿用检测到的编码
        content = None
        used_encoding = None
        for enc in encodings_to_try:
            try:
                with open(target_path, 'r', encoding=enc) as f:
                    content = f.read()
                    used_encoding = enc
                    break
            except Exception:
                continue
        if content is None:
            return toolResult(
                success=False, message="", content="",
                error=f"无法用常见编码读取文件（{', '.join(encodings_to_try)}），文件可能是二进制",
                tool_name="file_edit"
            )

        # 2. keepends=True 保真读取:保留每行原有的行尾换行符,
        #    否则重写后末尾换行丢失,行结构与原文件不一致,LLM 下次数行号会错位
        lines = content.splitlines(keepends=True)

        # 3. 行号校验:越界切片会静默追加到文件末尾,start_line=0 还会触发负索引切片,
        #    必须显式拒绝,并告诉 LLM 文件实际行数
        if start_line < 1 or end_line < start_line or end_line > len(lines):
            return toolResult(
                success=False, message="", content="",
                error=f"行号不合法: 文件共 {len(lines)} 行, 但收到 start_line={start_line}, end_line={end_line}, 请核对行号后重试",
                tool_name="file_edit"
            )

        start_idx = start_line - 1
        end_idx = end_line
        old_content = "".join(lines[start_idx:end_idx])
        # 4. 新内容按行拆分并补换行符(空字符串 = 删除该区间)
        new_lines = new_content.splitlines()
        if new_lines:
            new_lines = [line + "\n" for line in new_lines]

        # 生成 unified diff 前，先准备修改前后的完整行列表
        old_lines_for_diff = [line.rstrip("\r\n") for line in lines]

        new_lines_all = lines.copy()
        new_lines_all[start_idx:end_idx] = new_lines

        new_lines_for_diff = [line.rstrip("\r\n") for line in new_lines_all]

        # 生成 unified diff
        diff_text = "\n".join(
            difflib.unified_diff(
                old_lines_for_diff,
                new_lines_for_diff,
                fromfile=f"a/{file_path}",
                tofile=f"b/{file_path}",
                lineterm="",
                n=3,
            )
        )

        if not diff_text:
            diff_text = "（替换成功，但没有产生实际文本变化）"
        elif len(diff_text) > 20000:
            diff_text = diff_text[:20000] + "\n... diff 过长，已截断"

        # 真正应用修改
        lines = new_lines_all

        # 5. newline='' 禁止换行翻译,原行保持原字节(CRLF/LF 都不动)
        with open(target_path, 'w', encoding=used_encoding, newline='') as f:
            f.write("".join(lines))

        return toolResult(
            success=True,
            message=f"文件 '{target_path}' 的第 {start_line} 行到第 {end_line} 行已成功替换为新内容。",
            content=diff_text,
            data=old_content,
            tool_name="file_edit"
        )

    except Exception as e:
        return toolResult(
            success=False,
            message=f"错误：处理文件 '{file_path}' 时发生错误：{e}",
            content="",
            error=f"命令执行失败：{compress_error(str(e))}。请检查参数或跳过此步骤，建议如实告知用户",
            tool_name="file_edit"
        )


def create_file_tool(file_path: str, content: str, config:RunnableConfig) -> toolResult:
    target_path =relativePathToAbsolute(file_path,config)
    if os.path.exists(target_path):
        return toolResult(
            success=False,
            message=f"文件 '{target_path}' 已存在，无法创建新文件，请直接调用 file_edit 工具进行编辑。",
            content="",
            tool_name="create_file"
        )

    try:
        parent_dir = os.path.dirname(target_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        # 生成新建文件的 diff：从 /dev/null 到新文件
        new_lines = content.splitlines()
        diff_text = "\n".join(
            difflib.unified_diff(
                [],
                new_lines,
                fromfile="/dev/null",
                tofile=f"b/{file_path}",
                lineterm="",
                n=3,
            )
        )

        # 如果创建的是空文件，可以显示一个提示
        if not diff_text:
            diff_text = "（新建空文件）"

        # 防止新建文件内容太长，导致 diff 过大
        if len(diff_text) > 20000:
            diff_text = diff_text[:20000] + "\n... diff 过长，已截断"

        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return toolResult(
            success=True,
            message=f"已创建文件 '{target_path}' ",
            content=diff_text,
            tool_name="create_file"
        )

    except Exception as e:
        return toolResult(
            success=False,
            message=f"错误：创建文件 '{file_path}' 时发生错误",
            content="",
            error=f"命令执行失败：{compress_error(str(e))}。请检查参数或跳过此步骤，建议如实告知用户",
            tool_name="create_file"
        )


def delete_file_tool(file_path:str, config:RunnableConfig) -> toolResult:
    target_path =relativePathToAbsolute(file_path,config)
    if not os.path.exists(target_path):
        return toolResult(
            success=False,
            message=f"文件 '{target_path}' 不存在，无法删除。",
            content="",
            tool_name="delete_file"
        )
    old_content = ""
    try:
        for enc in encodings_to_try:
            try:
                with open(target_path, 'r', encoding=enc) as f:
                    old_content = f.read()
                    break
            except Exception:
                continue
    except Exception:
        # 如果读不了（比如二进制文件），标记为空，回滚时无法恢复
        old_content = ""
    os.remove(target_path)
    return toolResult(
        success=True,
        message=f"文件 '{target_path}' 已成功删除。",
        content="",
        data=old_content,
        tool_name="delete_file"
    )