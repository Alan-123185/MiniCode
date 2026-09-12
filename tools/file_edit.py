from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from utils.editFileTools import file_edit_tool, create_file_tool, delete_file_tool
from config.data import settings
from core.toolResult import toolResult
# 与 file_read 一致的多编码尝试列表,避免让 LLM 猜编码(猜错即失败,会引发重试)
encodings_to_try = settings.ENCODINGS_TO_TRY

# @tool
# def file_edit(
#     file_path: str,
#     start_line: int,
#     end_line: int,
#     new_content: str,
#     config:RunnableConfig
# ) -> toolResult:
#     """
#     按行号替换文件中的指定代码行。
#
#     使用前必须先读取带行号的文件内容，确保 start_line 和 end_line 基于最新文件。
#     删除连续多行时，务必在一次调用里用 start_line~end_line + 空字符串完成，不要逐行删
#     :param file_path: 要修改的文件相对路径。
#     :param start_line: 开始行号，从 1 开始计数。
#     :param end_line: 结束行号，从 1 开始计数，包含该行。
#     :param new_content: 替换后的新内容，可以是多行字符串。不要包含行号前缀。如果传空字符串 ""，表示删除这些行。
#     :return: 返回一个工具调用结果类
#
#     示例：
#     如果文件内容是：
#        1| import os
#        2|
#        3| def foo():
#        4|     a = 1
#        5|     return a
#
#     想把第 4 行改成：
#         a = 2
#
#     则调用：
#     file_path = "xxx.py"
#     start_line = 4
#     end_line = 4
#     new_content = "    a = 2"
#
#     想删除第 4 行：
#     file_path = "xxx.py"
#     start_line = 4
#     end_line = 4
#     new_content = ""
#
#     想在第 4 行后插入一行：
#     file_path = "xxx.py"
#     start_line = 4
#     end_line = 4
#     new_content = "    a = 1\n    print(a)"
#     """
#     return file_edit_tool(file_path, start_line, end_line, new_content,config)
#
#
#9.11 改用内容锚定的方法来修改文件，而不是之前的按行号修改，这样可以避免因为文件内容变化导致的行号不匹配问题。
@tool
def file_edit(
    file_path: str,
    old_content:str,
    new_content: str,
    config:RunnableConfig
) -> toolResult:
    """
    按内容锚定替换文件中的指定代码片段。

    使用前建议先读取最新文件内容，确保 `old_content` 与目标片段完全匹配。
    如果要删除内容，请将 `new_content` 传为空字符串 ""。
    :param file_path: 要修改的文件相对路径。
    :param old_content: 需要被替换的旧内容，可以是多行字符串，不要包含行号前缀。
    :param new_content: 替换后的新内容，可以是多行字符串，不要包含行号前缀；传空字符串 "" 表示删除匹配内容。
    :return: 返回一个工具调用结果类
    """
    return file_edit_tool(file_path,old_content,new_content,config)


@tool
def create_file(file_path: str, content: str, config:RunnableConfig) -> toolResult:
    """
    创建一个新文件并写入指定内容；如果目标文件已存在，则返回错误。

    该工具用于一次性新建文件，不负责基于旧内容做增量修改。

    :param file_path: 要创建的文件相对路径。
    :param content: 要写入文件的完整内容，可包含多行文本。
    :param config: 运行时配置。
    :return: 返回一个工具调用结果对象。
    """
    return create_file_tool(file_path , content , config)



@tool
def delete_file(file_path:str,config:RunnableConfig) -> toolResult:
    """
    删除指定的文件。

    :param file_path: 要删除的文件相对路径。
    :return: 返回一个工具调用结果类
    """
    return delete_file_tool(file_path,config)