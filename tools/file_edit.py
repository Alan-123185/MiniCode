from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from utils.editFileTools import file_edit_tool, create_file_tool, delete_file_tool
from config.data import settings
from core.toolResult import toolResult

# 与 file_read 一致的多编码尝试列表,避免让 LLM 猜编码(猜错即失败,会引发重试)
encodings_to_try = settings.ENCODINGS_TO_TRY

class FileEditArgs(BaseModel):
    file_path: str = Field(description="要修改的文件相对路径。")
    old_content: str = Field(
        description="需要被替换的旧内容，必须至少包含5行（除非整个文件小于5行）：以目标片段为中心，连同前后相邻代码一起作为上下文传入，确保在文件中唯一命中（短片段极易多处命中而被拒绝）。例外：若要替换整个文件内容，可传入全文。不要包含行号前缀。"
    )
    new_content: str = Field(
        description='替换后的新内容，可为多行字符串；传空字符串 "" 表示删除匹配内容。'
    )


@tool(args_schema=FileEditArgs)
def file_edit(
    file_path: str,
    old_content:str,
    new_content: str,
    config:RunnableConfig
) -> toolResult:
    """
    按内容锚定替换文件中的指定代码片段。
    使用前必须先读取最新文件内容，确保 `old_content` 与目标片段完全匹配。
    如果要删除内容，请将 `new_content` 传为空字符串 ""。
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