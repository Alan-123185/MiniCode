import json
from langchain_mcp_adapters.client import MultiServerMCPClient
from config.data import settings
from tools.sub_agent import  search_sub_agent
from tools.OriginalContentTool import get_original_content_by_tool_call_id,get_original_content_by_memory_id
from tools.file_read import readfile, listfiles, code_outline
from tools.file_search import search_file_by_keyword, search_code_by_keyword
from tools.command import run_code,execute_command
from tools.file_edit import file_edit, create_file, delete_file
from tools.undo_file_edit import undo_operationgroup, query_operationgroup
from utils.MessageTool import count_tokens

"""
9.26 MCP 工具注册
"""


async def create_tool() -> list:
    """
    创建一个 MultiServerMCPClient 实例，并注册一组工具函数。
    """
    mcp_tools = await get_mcp_tools()
    tools=[
        readfile,
        listfiles,
        search_code_by_keyword,
        search_file_by_keyword,
        file_edit,
        delete_file,
        create_file,
        execute_command,
        undo_operationgroup,
        query_operationgroup,
        get_original_content_by_tool_call_id,
        get_original_content_by_memory_id,
        run_code,
        search_sub_agent,
        code_outline,
        *mcp_tools  # 将 MCP 工具列表展开并添加到 tools 列表中
           ]
    return tools



tools_need_to_confirm = ["file_edit", "execute_command", "delete_file", "create_file", "undo_operationgroup"]

compatable_tools=[
                  "readfile",
                  "listfiles",
                  "search_code_by_keyword",
                  "search_file_by_keyword",
                  "get_original_content_by_tool_call_id",
                  "get_original_content_by_memory_id",
                  "code_outline",
                  "file_edit",
                  "delete_file",
                  "create_file",
                  "execute_command",
                  "run_code"
                  ]


tools:list=[]
tools_by_name:dict={}

def get_tools_by_name():
    return {tooln.name: tooln for tooln in tools}


async def init_tools():
    global tools
    new_tools = await create_tool()
    tools.clear()
    tools.extend(new_tools)  # 原地更新，已 import 它的模块引用的还是同一个 list 对象
    global tools_by_name
    new_tools_by_name = get_tools_by_name()
    tools_by_name.clear()
    tools_by_name.update(new_tools_by_name)
    settings.TOOL_SCHEMA_TOKENS=count_tokens(get_schema())


"""
探索型子代理的工具注册
"""




async def get_mcp_tools() -> list:
    client = MultiServerMCPClient(
        {
            "agent-search": {
                "command": str(settings.node_path),
                "args": [
                    str(settings.index_path),
                ],
                "transport": "stdio",
            }
        }
    )
    mcp_tools = await client.get_tools()
    allowed_names = {
        "free_search"
    }
    mcp_tools=[
        tool for tool in mcp_tools if tool.name in allowed_names
    ]
    return mcp_tools


def get_schema() -> str:
    """`
    获取所有工具的 schema 信息
    """
    ret=[]
    for t in tools:
        # 参数 schema：优先 args，兜底 args_schema
        params = getattr(t, "args", None)
        if not params:
            schema_obj = getattr(t, "args_schema", None)
            if schema_obj is not None:
                try:
                    params = schema_obj.model_json_schema()
                except Exception:
                    params = {}
            else:
                params = {}

        # 工具级描述：description 可能为 None
        desc = getattr(t, "description", None) or ""
        ret.append( {
            "type": "function",
            "function": {
                "name": t.name,
                "description": desc,
                "parameters": params,
            }
        })
    return json.dumps(ret, ensure_ascii=False)


# if __name__ == "__main__":
#     import asyncio
#
#     async def main():
#         tools = await create_tool()
#         for tool in tools:
#             print(f"Registered tool: {tool.name}")
#
#     asyncio.run(main())