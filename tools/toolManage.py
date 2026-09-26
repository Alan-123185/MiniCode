from langchain_mcp_adapters.client import MultiServerMCPClient
from tools.OriginalContentTool import get_original_content_by_tool_call_id, get_original_content_by_compressed_content
from tools.file_read import readfile, listfiles, code_outline
from tools.file_search import search_file_by_keyword, search_code_by_keyword
from tools.command import run_code,execute_command
from tools.file_edit import file_edit, create_file, delete_file
from tools.undo_file_edit import undo_operationgroup, query_operationgroup

"""
9.26 MCP 工具注册
"""
async def create_tool():
    """
    创建一个 MultiServerMCPClient 实例，并注册一组工具函数。
    """
    client=MultiServerMCPClient(
        {  # 传入服务配置字典
            "agent-search": {  # 定义一个名为 agent-search 的 MCP 服务
                "transport": "stdio",  # 使用标准输入输出作为通信方式
                "command": "npx.cmd",  # 在 Windows 上通过 npx.cmd 启动命令
                "args": ["-y", "agent-search-mcp"],  # 传给 npx 的参数，自动安装并启动 agent-search-mcp
            }
        }
    )
    mcp_tools = await client.get_tools()
    allowed_names = {
        "free_search",
        "free_extract",
    }
    mcp_tools=[
        tool for tool in mcp_tools if tool.name in allowed_names
    ]

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
           get_original_content_by_compressed_content,
           run_code,
           code_outline,
           *mcp_tools  # 将 MCP 工具列表展开并添加到 tools 列表中
           ]
    return tools


def unsafe_tool():
    tools_need_to_confirm = ["file_edit", "execute_command", "delete_file", "create_file", "undo_operationgroup"]
    return tools_need_to_confirm