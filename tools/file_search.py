from langchain.tools import tool
import subprocess
from langchain_core.runnables import RunnableConfig
from config.data import settings
from config.dependencies import get_session
from core.toolResult import toolResult
from utils.filePathTools import relativePathToAbsolute, absolutePathToRelative


@tool
def search_code_by_keyword(config:RunnableConfig,query: str, path: str = ".") -> toolResult:
    """
    在项目中搜索关键词或正则，返回匹配行及其所在文件相对路径（具体代码）
    :param query: 搜索关键词或正则表达式
    :param path: 相对路径，默认为"."，表示根目录
    :return: 返回一个工具调用结果类，包含搜索结果
    """
    # path=relativePathToAbsolute(path)

    result = subprocess.run(
        [
            str(settings.rg_path),
            "--line-number",
            "--max-count",
            "50",
            query,
            path
        ],
        cwd=(get_session(config)).workplace,
        capture_output=True,
        text=True,
        encoding="utf-8"
    )
    return toolResult(
        success=True,
        message=f"在目录 {path} 下搜索关键词 '{query}' 的结果",
        content=result.stdout or "no find"
    )


@tool
def search_file_by_keyword(query: str,config:RunnableConfig , path: str = ".") -> toolResult:
    """
    按文件名搜索:查找文件名包含关键字的文件的相对路径(不检查文件内容)

    返回的 path 可以直接作为 readfile 的 path 参数，
    用于读取对应文件内容。

    如果已经通过本工具获得了明确的文件路径，
    后续读取该文件时应直接调用 readfile，
    无需再次调用 listfiles 搜索文件。

    :param query: 文件名中包含的关键字,如"student"、"徐姝"
    :param path: 相对路径,默认为"."，表示根目录
    :return: 返回文件名包含关键字的文件路径列表
    """
    target =relativePathToAbsolute(path,config)
    if not target.exists():
        return toolResult(success=False, content="", error=f"目录不存在: {target}",
                          tool_name="search_file_by_keyword")
    matches = []
    for p in target.rglob("*"):
        if p.is_file() and query.lower() in p.name.lower():
            # 输出相对路径,LLM 后续调 readfile 才顺利
            matches.append(str(absolutePathToRelative(str(p),config)))
    matches.sort()
    return toolResult(
        success=True,
        message=f"文件名包含关键字 '{query}' 的文件路径",
        content="\n".join(matches) if matches else "no find",
        tool_name="search_file_by_keyword"
    )




#这个需要rag技术，到时候写
@tool
def search_code_by_meaning(query):
    """
       在项目中根据语义搜索代码片段
    """
    pass

