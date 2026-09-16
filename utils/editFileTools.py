import os
from difflib import SequenceMatcher, unified_diff
from pathlib import Path
from langchain_core.runnables import RunnableConfig
from config.data import settings
from core.toolResult import toolResult
from utils.MessageTool import compress_error
from utils.filePathTools import relativePathToAbsolute
from utils.normalCodeTool import normalize_line

encodings_to_try=settings.ENCODINGS_TO_TRY
thread_hold=settings.THREAD_HOLD
min_hold=settings.MIN_HOLD

def file_edit_tool(
    file_path: str,
    old_content:str,
    new_content:str,
    config:RunnableConfig
) -> toolResult:
    target_path =relativePathToAbsolute(file_path,config)
    if not os.path.exists(target_path):
        return toolResult(success=False, error=f"文件 '{target_path}' 不存在。如想增加文件请调用create_file工具")
    file_content=None
    new_lines=new_content.splitlines(keepends=True)
    for enc in encodings_to_try:
        try:
            with open(target_path, 'r', encoding=enc, newline='') as f:
                file_content = f.read()
                used_encoding = enc
                break
        except Exception :
            continue
    if file_content is None:
        return toolResult(
            success=False,
            error=f"无法用常见编码读取文件（{', '.join(encodings_to_try)}），文件可能是二进制",
            tool_name="file_edit"
        )
    # newline='' 原样读入后,CRLF 文件里的 old/new_content 需转成同样的行尾风格才能匹配
    if '\r\n' in file_content:
        old_content = old_content.replace('\r\n', '\n').replace('\n', '\r\n')
        new_content = new_content.replace('\r\n', '\n').replace('\n', '\r\n')
        new_lines = new_content.splitlines(keepends=True)
    file_lines=file_content.splitlines(keepends=True)
    try:
        #第一级，精确匹配
        count = file_content.count(old_content)
        if count==1:
            return exchange(count,target_path, old_content, new_content, file_content, used_encoding, file_path)
        old_lines=old_content.splitlines(keepends=True)
        file_lines=file_content.splitlines(keepends=True)
        n=len(old_lines)
        normalize_old_lines=normalize_line(old_lines)
        normalize_file_lines=normalize_line(file_lines)
        match,like=search(normalize_old_lines,normalize_file_lines)
        if len(match)==1:
            start_idx = match[0]
            end_idx = start_idx + n
            diff_text=replace(new_lines,normalize_file_lines,start_idx,end_idx,target_path,used_encoding,file_path)
            return toolResult(
                success=True,
                message=f"文件 '{target_path}' 中旧内容已成功替换为新内容。",
                content=diff_text,
                tool_name="file_edit"
            )
        elif len(match) > 1:
            return toolResult(
                success=False,
                error=f"文件 '{target_path}' 中旧内容出现了多次，无法确定替换位置，请提供更多上下文信息以帮助定位旧内容。",
                tool_name="file_edit"
            )
        else:
            if len(like)>0:
                return toolResult(
                    success=False,
                    error=f"文件 '{target_path}' 中未找到旧内容，存在以下相似内容供参考：{["\n".join(file_lines[lk:lk + n]) for lk in like]}",
                    tool_name="file_edit"
                )
            return toolResult(
                success=False,
                error=f"文件 '{target_path}' 中未找到旧内容，请检查提供的旧内容是否正确。",
                tool_name="file_edit"
            )
    # 第四级，最终模糊匹配，到时候再写
    except Exception as e:
        return toolResult(
            success=False,
            error=f"执行失败：{compress_error(str(e))}。请检查参数或跳过此步骤，建议如实告知用户",
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
            unified_diff(
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

        with open(target_path, 'w', encoding='utf-8', newline='') as f:
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
            error=f"执行失败：{compress_error(str(e))}。请检查参数或跳过此步骤，建议如实告知用户",
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





#普通交换函数
def exchange(count:int,target_path:Path, old_content:str, new_content:str, file_content:str, used_encoding:str, file_path:str) -> toolResult:
        old_file_lines = file_content.splitlines()
        file_content = file_content.replace(old_content, new_content, 1)
        diff_text = "\n".join(
            unified_diff(
                old_file_lines,
                file_content.splitlines(),
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
        with open(target_path, 'w', encoding=used_encoding, newline='') as f:
            f.write(file_content)
        return toolResult(
            success=True,
            message=f"文件 '{target_path}' 已成功替换为新内容",
            content=diff_text,
            tool_name="file_edit"
        )


#搜索函数+贪心聚类
def search(old_lines: list[str], file_lines: list[str]) -> tuple[list[int], list[int]]:
    matchs = []
    likes = []
    length = len(old_lines)

    # 1. 单次遍历，收集所有达标的候选项 (索引, 相似度)
    for i in range(len(file_lines) - length + 1):
        ratio = SequenceMatcher(None, old_lines, file_lines[i:i + length]).ratio()
        if ratio >= thread_hold:
            matchs.append((i, ratio))
        elif ratio >= min_hold:
            likes.append((i, ratio))

    # 2. 极简贪心聚类核心函数
    def greedy_cluster(candidates, window_size):
        if not candidates:
            return []
        # 核心动作 A：按相似度从高到低排序（优先选最像的）
        candidates.sort(key=lambda x: x[1], reverse=True)

        result_indices = []
        # 核心动作 B：遍历排好序的列表，如果和已选中的不重叠，才保留
        for i, ratio in candidates:
            # 检查当前的 i，是否和 result_indices 里已经选中的任何一个索引距离小于 window_size
            is_overlap = any(abs(i - selected_i) < window_size for selected_i in result_indices)
            if not is_overlap:
                result_indices.append(i)  # 只保留纯索引 (int)
        return result_indices

    # 3. 分别对 match 和 like 进行聚类去重，返回纯索引列表
    ret_matchs = greedy_cluster(matchs, length)
    ret_likes = greedy_cluster(likes, length)

    return ret_matchs, ret_likes



#替换函数
def replace(new_lines:list[str],file_lines:list[str],start:int,end:int,target_path:Path,used_encoding:str,file_path:str) -> str:
    old_lines_for_diff = [line.rstrip("\r\n") for line in file_lines]
    file_lines[start:end] = new_lines
    with open(target_path, 'w', encoding=used_encoding, newline='') as f:
        f.write("".join(file_lines))
    diff_text = "\n".join(
        unified_diff(
            old_lines_for_diff,
            [line.rstrip("\r\n") for line in file_lines],
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            lineterm="",
            n=3
        )
    )
    if not diff_text:
        diff_text = "（替换成功，但没有产生实际文本变化）"
    elif len(diff_text) > 20000:
        diff_text = diff_text[:20000] + "\n... diff 过长，已截断"
    return diff_text
