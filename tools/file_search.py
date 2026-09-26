import subprocess
from pathlib import Path

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from tree_sitter_analyzer.ast_path import ASTPathNavigator

from config.data import settings
from config.dependencies import get_session
from core.toolResult import toolResult
from utils.commandSafe import truncate_output, smart_decode
from utils.errormanagerTool import compress_error
from utils.filePathTools import relativePathToAbsolute, absolutePathToRelative


EXCLUDE_GLOBS = [
    "!.git",
    "!node_modules",
    "!__pycache__",
    "!.venv",
    "!venv",
    "!dist",
    "!build",
    "!*.min.js",
    "!*.min.css",
    "!*.map",
    "!*.lock",
    "!package-lock.json",
    "!yarn.lock",
    "!.DS_Store",
    "!*.pyc",
    "!*.pyo",
    "!*.so",
    "!*.dll",
    "!*.exe",
    "!*.bin",
]

EXCLUDE_DIRS = [
    "!.git/**",
    "!node_modules/**",
    "!__pycache__/**",
    "!.venv/**",
    "!venv/**",
    "!dist/**",
    "!build/**",
    "!.idea/**",
    "!.vscode/**",
    "!.tox/**",
    "!.mypy_cache/**",
    "!.pytest_cache/**",
    "!*.egg-info/**",
    "!.eggs/**",
]

class SearchCodeInput(BaseModel):
   query:str=Field(...,description="要搜索的关键词或正则表达式，例如 'UserService'、'DELETE FROM'、'TODO'、'auth.*token'")
   path:str=Field(default=".", description="相对路径，默认 '.' 表示工作区根目录；建议缩小到具体目录，避免搜索范围过大")
   max_count:int=Field(default=settings.RG_SEARCH_MAX_COUNT, gt=10, lt=100, description="最大返回结果数，llm可以根据需要调整，默认值为 50")
   file_type:str=Field(default="", description="可选参数，指定搜索文件类型；如指定读md文件，file_type='md' ，如果不指定，则搜索所有类型")



"""
代码搜索增强 9.25
"""
@tool(args_schema=SearchCodeInput)
def search_code_by_keyword(config:RunnableConfig,query: str, path: str = ".", max_count: int =settings.RG_SEARCH_MAX_COUNT,file_type:str="") -> toolResult:
    """
    这是“正文搜索”，不是“文件名搜索”。
    在代码内容中搜索关键词/正则，返回文件路径，代码父级结构及范围行，代码匹配所在行。
    适用场景：
    - 你知道一个关键词、函数名、报错文本、字段名或正则表达式，但不知道具体文件；
    - 需要定位代码实现或引用位置；
    - 需要在某个目录下快速查找相关逻辑。
    :return: 返回一个工具调用结果类，包含搜索结果
    """

    cmd = [str(settings.rg_path),
           "--line-number",  # 显示匹配行的行号
           "--no-heading",  # 不按文件分组，每行前面直接带文件名
           "--with-filename",  # 关键：强制总是输出文件名
           "--smart-case",  # 智能大小写：搜索词全小写就忽略大小写，有大写就区分
           "--max-count",str(max_count),
           query,
           path
           ]
    #排除噪音目录
    for g in EXCLUDE_GLOBS:
        cmd.extend(["--glob", g])
    if file_type:
        cmd.extend(["--type",file_type])
    try:
        result = subprocess.run(
            cmd,
            cwd=(get_session(config)).workplace,
            capture_output=True,
            timeout=settings.RG_SEARCH_TIMEOUT
        )
    except subprocess.TimeoutExpired:
        return toolResult(
            success=False,
            error=f"搜索关键词 '{query}' 超时，请尝试缩小搜索范围或关键词。",
            tool_name="search_code_by_keyword"
        )
    except Exception as e:
        return toolResult(
            success=False,
            error=f"搜索关键词 '{query}' 时发生错误: {compress_error(str(e))}",
            tool_name="search_code_by_keyword"
        )
    if result.returncode == 1:
        return toolResult(
            success=True,
            content=f"{path} 下未找到 '{query}' 的匹配",
            tool_name="search_code_by_keyword"
        )
    if result.returncode > 1:
        return toolResult(
            success=False,
            message=f"搜索出错: {truncate_output(smart_decode(result.stderr.strip()))}",
            content="",
            tool_name="search_code_by_keyword"
        )
    output=smart_decode(result.stdout)
    lines=output.strip().splitlines()
    search_results = [line.split(":",2) for line in lines]
    ret=[]
    for file_path, line_number, code_line in search_results:
        try:
            scope_dict = parent_scope((relativePathToAbsolute(file_path, config)), int(line_number))
        except Exception as e:
            scope_dict=None
        if not scope_dict:
            ret.append(f"{file_path}: module:{Path(file_path).name} {code_line} (in {line_number})")
        else:
            ret.append(f"{file_path}: {scope_dict["kind"]}:{scope_dict['name']}({scope_dict["lines"][0]}-{scope_dict["lines"][1]})   {code_line} (in {line_number})")
    return toolResult(
        success=True,
        message=f"在目录 {path} 下搜索关键词 '{query}' 的结果",
        content="\n".join(ret),
        tool_name="search_code_by_keyword"
    )


class SearchFileInput(BaseModel):
    query: str = Field(..., description="要搜索的文件名关键字，例如 'user'、'session'、'router'、'auth'")
    file_type: str = Field(default="", description="可选参数，指定搜索文件类型；如指定读md文件，file_type='md' ，如果不指定，则搜索所有类型")
    path: str = Field(default=".", description="相对路径，默认 '.' 表示工作区根目录；可缩小到 service/ 或 routers/ 等目录")



@tool(args_schema=SearchFileInput)
def search_file_by_keyword(query: str,config:RunnableConfig ,file_type: str="", path: str = ".") -> toolResult:
    """
    按“文件名”搜索，大小写不敏感，比如搜索 "user" 和 "USer" 返回的结果相同；不检查文件内容。
    这是“定位文件”工具，不是代码搜索工具。
    :return: 返回一个工具调用结果类，包含搜索结果
    """
    target =relativePathToAbsolute(path,config)
    if not target.exists():
        return toolResult(
            success=False,
            error=f"目录不存在: {target}",
            tool_name="search_file_by_keyword"
          )
    cmd=[
        str(settings.rg_path),
        "--files",
        "--max-count", str(settings.RG_SEARCH_MAX_COUNT),
        "--glob", f"*{query}*",
        path
    ]
    for g in EXCLUDE_DIRS:
        cmd.extend(["--glob", g])
    try:
        result = subprocess.run(
            cmd,
            cwd=(get_session(config)).workplace,
            capture_output=True,
            timeout=settings.RG_SEARCH_TIMEOUT
        )
    except subprocess.TimeoutExpired:
        return toolResult(
            success=False,
            error=f"搜索关键词 '{query}' 超时，请尝试缩小搜索范围或关键词。",
            tool_name="search_file_by_keyword"
        )
    except Exception as e:
        return toolResult(
            success=False,
            error=f"搜索关键词 '{query}' 时发生错误: {compress_error(str(e))}",
            tool_name="search_file_by_keyword"
        )
    if result.returncode == 1:
        return toolResult(
            success=True,
            content=f"{path} 下未找到 '{query}' 的匹配",
            tool_name="search_file_by_keyword"
        )
    if result.returncode > 1:
        return toolResult(
            success=False,
            message=f"搜索出错: {truncate_output(smart_decode(result.stderr.strip()))}",
            content="",
            tool_name="search_file_by_keyword"
        )
    output=smart_decode(result.stdout)
    matches = output.strip().splitlines()
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







def parent_scope(file_path: Path, line: int, self_name: str | None = None) -> dict | None:
    """使用AST返回某行代码的上一级命名结构。上一级不存在（顶层）时返回 None """
    nav=ASTPathNavigator()
    chain = [
        n for n in nav.path_at_line(str(file_path), line).path
        if n.is_named_scope and n.name
    ]
    # 目标本身若是函数/类定义，把自己从链里剔掉
    if self_name:
        chain = [n for n in chain
                 if not (n.name == self_name and n.start_line == line)]
    if not chain:
        return  None
    p = chain[-1]
    kind = p.type.replace("_definition", "").replace("_declaration", "")
    return {"kind": kind, "name": p.name, "lines": [p.start_line, p.end_line]}