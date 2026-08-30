from typing import  Literal

from pydantic import BaseModel, Field


class ReadFileParams(BaseModel):
    """读取单个文本文件内容，用于查看代码、配置与日志。返回带行号的文本内容。"""

    tool_name: Literal["readfile"] = "readfile"
    file_path: str = Field(..., description="文件相对路径，必须是仓库内的相对路径")


class BaiduSearchParams(BaseModel):
    """进行实时联网搜索，适用于需要查最新信息、时效性问题或外部事实检索。"""

    tool_name: Literal["baidu_search"] = "baidu_search"
    question: str = Field(..., description="要搜索的关键词或问题描述")


class RunCommandParams(BaseModel):
    """在指定工作目录执行 shell 命令，用于运行测试、编译、脚本和诊断命令。"""

    tool_name: Literal["run_command"] = "run_command"
    command: str = Field(..., description="要执行的 shell 命令")
    cwd: str = Field(..., description="命令执行的工作目录，相对路径或绝对路径")
    stdin_input: str | None = Field(default=None, description="可选的标准输入内容；适用于需要交互输入的脚本")


class ListFilesParams(BaseModel):
    """查看目录下的一级文件与子目录结构，帮助定位目标文件和目录。"""

    tool_name: Literal["listfiles"] = "listfiles"
    folder_path: str = Field(default=".", description="要浏览的文件夹相对路径，默认是当前工作目录")


class SearchCodeByKeywordParams(BaseModel):
    """在代码中按关键词或正则搜索，返回命中行及所在文件，适合定位实现位置。"""

    tool_name: Literal["search_code_by_keyword"] = "search_code_by_keyword"
    query: str = Field(..., description="搜索关键词或正则表达式")
    path: str = Field(default=".", description="搜索的根目录，相对路径")


class SearchFileByKeywordParams(BaseModel):
    """按文件名搜索目标文件，返回候选文件路径，适合快速找到需要阅读的文件。"""

    tool_name: Literal["search_file_by_keyword"] = "search_file_by_keyword"
    query: str = Field(..., description="文件名中包含的关键字")
    path: str = Field(default=".", description="搜索的根目录，相对路径")


class SearchCodeByMeaningParams(BaseModel):
    """按语义搜索代码片段，适合在不知道精确关键字时定位功能实现。"""

    tool_name: Literal["search_code_by_meaning"] = "search_code_by_meaning"
    query: str = Field(..., description="语义搜索的关键词或需求描述")


class FileEditParams(BaseModel):
    """按行号修改文件内容，适合精确修复代码、替换文本或删除指定行。"""

    tool_name: Literal["file_edit"] = "file_edit"
    file_path: str = Field(..., description="要修改的文件路径")
    start_line: int = Field(..., description="开始行号，从 1 开始计数")
    end_line: int = Field(..., description="结束行号，从 1 开始计数，包含该行")
    new_content: str = Field(..., description="替换后的新内容；空字符串表示删除目标行")


class CreateFileParams(BaseModel):
    """创建一个新文件，用于初始化脚本、配置、文档或者新代码文件。"""

    tool_name: Literal["create_file"] = "create_file"
    file_path: str = Field(..., description="要创建的文件相对路径")
    content: str = Field(..., description="文件内容")


class DeleteFileParams(BaseModel):
    """删除指定文件，通常用于清理中间产物、无用文件或者回滚新建文件。"""

    tool_name: Literal["delete_file"] = "delete_file"
    file_path: str = Field(..., description="要删除的文件相对路径")


class UndoOperationGroupParams(BaseModel):
    """按会话中的操作组回滚到指定版本，适合撤销最近一段错误修改。"""

    tool_name: Literal["undo_operationgroup"] = "undo_operationgroup"
    target_group_id: str = Field(..., description="需要回滚到的操作组 ID")
    session_id: str = Field(..., description="当前会话 ID")


class QueryOperationGroupParams(BaseModel):
    """查询当前会话内的操作组列表，用于决定回滚到哪个版本。"""

    tool_name: Literal["query_operationgroup"] = "query_operationgroup"
    session_id: str = Field(..., description="当前会话 ID")


class GitParams(BaseModel):
    """执行 git 命令，用于查看提交记录、状态、差异、分支和代码版本管理。"""

    tool_name: Literal["git"] = "git"
    command: str = Field(default="status", description="要执行的 git 子命令，如 status、log、diff、checkout")
    cwd: str = Field(default=".", description="git 执行的工作目录，相对路径或绝对路径")

