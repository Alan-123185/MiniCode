from langchain.agents import create_agent
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from config.modelConfig import model_config
from core.toolResult import toolResult
from prompt.subAgent.search_agent_prompt import SEARCH_AGENT_PROMPT
from tools.toolManage import search_agent_tools




"""子代理工具定义。

该模块提供一个只读的代码探索型子代理，用于在主代理无法直接深挖代码时，
执行搜索、定位和依赖分析等任务，并将结果以工具调用的形式返回。
"""
class searchSubAgentTask(BaseModel):
    """子代理任务参数模型。
    该模型定义了探索型子代理所需的最小输入信息，包括任务目标、背景信息、
    关注范围、约束条件以及期望输出，以便在 LangChain 工具调用中进行参数校验。
    """
    mission: str = Field(..., description="子代理的目标或任务描述")
    background: str | None = Field(None, description="子代理所需要的上下文信息，可选")
    scope: list[str] | None = Field(None, description="子代理应该重点关注的领域或方面，可选")
    constraints: list[str] | None = Field(default_factory=list, description="子代理需要遵守的约束条件列表")
    expected_output: str | None = Field(None, description="子代理预期的输出格式或结果，可选")


@tool(args_schema=searchSubAgentTask)
async def search_sub_agent(
    mission: str,
    background: str | None = None,
    scope: list[str] | None = None,
    constraints: list[str] | None = None,
    expected_output: str | None = None,
) -> toolResult:
    """创建并执行一个只读的代码探索型子代理。

    该工具会根据主代理提供的任务描述、背景、范围、约束和输出要求，
    构造一个以代码搜索与定位为核心的子代理，执行针对仓库和代码依赖的
    只读分析。子代理不会修改代码，也不会编造路径、行号或符号信息。
    """
    tools_for_sub=await search_agent_tools()
    # 这里可以添加子代理的处理逻辑
    sub_agent=create_agent(
        model=model_config["value"],
        tools=tools_for_sub,
        system_prompt="你是代码探索子代理，为主代理工作，仅执行只读操作，负责搜索、定位与依赖分析。不得修改代码，不得输出搜索过程，不得编造路径、行号或符号。"
    )
    user_msg=SEARCH_AGENT_PROMPT.format(
        mission=mission,
        background=background or "无",
        scope=", ".join(scope) if scope else "无",
        constraints=", ".join(constraints) if constraints else "无",
        expected_output=expected_output or "无"
    )
    result=await sub_agent.ainvoke(
        {
            "messages": [{"role": "user", "content": user_msg}]
        }
    )
    return toolResult(
        success=True,
        message="子代理 search_sub_agent 执行成功",
        content=result["messages"][-1].content,
        tool_name="search_sub_agent"
    )




