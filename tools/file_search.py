
import subprocess
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from config.data import settings
from config.dependencies import get_session
from core.toolResult import toolResult
from utils.filePathTools import relativePathToAbsolute, absolutePathToRelative



@tool
def search_code_by_keyword(config:RunnableConfig,query: str, path: str = ".") -> toolResult:
    """
    在代码内容中搜索关键词/正则，返回“匹配代码行 + 所在文件相对路径”。

    这是“正文搜索”，不是“文件名搜索”。
    适用场景：
    - 你知道一个关键词、函数名、报错文本、字段名或正则表达式，但不知道具体文件；
    - 需要定位代码实现或引用位置；
    - 需要在某个目录下快速查找相关逻辑。

    :param query: 要搜索的关键词或正则表达式，例如 "UserService"、"DELETE FROM"、"TODO"、"auth.*token"
    :param path: 相对路径，默认 "." 表示工作区根目录；建议缩小到具体目录，避免搜索范围过大

    :return: 返回一个工具调用结果类，包含搜索结果
    """
    # path=relativePathToAbsolute(path)

    result = subprocess.run(
        [
            str(settings.rg_path),
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
    按“文件名”搜索，不关心大小写 返回文件的相对路径；不检查文件内容。

    这是“定位文件”工具，不是代码搜索工具。

    :param query: 文件名中的关键字，例如 "user"、"session"、"router"、"auth"
    :param path: 相对路径，默认 "." 表示工作区根目录，可缩小到 service/ 或 routers/ 等目录

    :return: 返回一个工具调用结果类，包含搜索结果
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

