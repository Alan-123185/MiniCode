from langgraph.types import interrupt
from loguru import logger
from tree_sitter_analyzer.core.analysis_engine import UnifiedAnalysisEngine
from tree_sitter_analyzer.core.request import AnalysisRequest

from core.InterruptInfo import InterruptInfo
from config.data import settings
from core.toolResult import toolResult
from core.toolStatusEvent import toolstatusEvent
from mappercommon.summary import Summary
from service.summaryService import summaryService
from states.OverallState import OverAllState
from tools.OriginalContentTool import get_original_content_by_compressed_content, get_original_content_by_tool_call_id
from tools.command import execute_command, run_code
from tools.file_edit import file_edit, create_file, delete_file
from tools.file_read import readfile, listfiles
from tools.web_search import baidu_search, Jina_search
from tools.file_search import search_code_by_keyword, search_file_by_keyword
from langchain_core.messages import ToolMessage, HumanMessage
from langgraph.config import get_stream_writer
from langchain_core.runnables import RunnableConfig  # 引入 Config 类型
from tools.undo_file_edit import undo_operationgroup, query_operationgroup
from utils.errormanagerTool import compress_error
from utils.commandSafe import is_command_safe

"""

这里需要传入工具列表.....


"""
tools=[baidu_search,
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
       Jina_search
       ]
summary_service=summaryService()
tools_need_to_confirm=["file_edit","execute_command","delete_file","create_file","undo_operationgroup"]
max_retry_time=settings.MAX_TOOL_CALLS
# try:
#     writer = get_stream_writer()
# except Exception:
#     writer = None
tools_by_name = {}
for tooln in tools:
    tools_by_name[tooln.name] = tooln


# 注意：这里增加了 config: RunnableConfig 参数，这是触发事件的关键！
async def tool_node(state: OverAllState, config: RunnableConfig) -> OverAllState:
    tool_failures = dict(state.tool_call_count or {})
    output = []
    step = []
    last_message = state.messages[-1]

    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        tool_call_id = tool_call["id"]
        tool = tools_by_name.get(tool_name,"不存在该工具，请检查工具命名后重试")

        # ================= 1. 处理需要确认的工具 =================
        if  tool_name in tools_need_to_confirm and not (tool_name == "execute_command" and is_command_safe(tool_args.get("command", ""), tool_args.get("stdin_input", None))) :
            # interrupt 会暂停图的执行，等待外部通过 update_state 或 Command 恢复
            decision = interrupt(
                InterruptInfo(
                    tool_name=tool_name,
                    tool_args=tool_args,
                    message=f"I want to use {tool_name}, do you agree?"
                )
            )

            if decision != "yes":
                # 【自定义事件】实时通知前端：用户拒绝了
                _emit_tool_status(
                    toolstatusEvent(status=settings.tool_refused, tool_name=tool_name, args=tool_args, result=None,session_id=config.get("configurable", {}).get("thread_id"))
                )

                output.append(ToolMessage(
                    content=f"用户拒绝了 {tool_name} 的调用,请如实告知用户,如果任务无法进行,可以自行决定是否继续",
                    tool_call_id=tool_call_id,
                    name=tool_name
                ))
                step.append(f"user refused tool:{tool_name}")
                continue

        # ================= 2. 执行工具 =================
        step.append(f"try to use tool:{tool_name}")

        # 【自定义事件】实时通知前端：开始尝试调用
        _emit_tool_status(
            toolstatusEvent(status=settings.tool_try, tool_name=tool_name, args=tool_args, result=None,session_id=config.get("configurable", {}).get("thread_id"),user_prompt=state.input)
        )
        try:
            toolresult = await tool.ainvoke(tool_args,config=config)
            logger.info(f"调用工具 {tool_name} 成功，结果: {toolresult}")
        except Exception as e:
            logger.error(f"调用工具 {tool_name} 时发生错误: {e}")
            toolresult = toolResult(success=False, message=f"调用工具 {tool_name} 时发生错误: {compress_error(str(e))}")
        logger.info(str(toolresult))
        toolresult_for_llm = toolresult
        # ================= 3. 处理执行结果 =================
        if toolresult.success:
            #在这里提前把压缩的 readfile 结果存储到 summary_service 中，方便后续降级使用
            if tool_name=="readfile" :
                if not tool_args["start_line"] and not tool_args["end_line"] and "为防止上下文爆炸"not in toolresult.content:
                    compress_read_content=await _compress_read_result(tool_args["file_path"])
                    summary_service.add_Tool_summary(Summary(
                        session_id=config.get("configurable", {}).get("thread_id"),
                        tool_call_id=tool_call_id,
                        content=toolresult.content,
                        compressed_content=compress_read_content,
                        message_type=settings.LLM_MESSAGE_TYPE_TOOL,
                    ))
            # 尝试覆盖之前的所有出错消息，保持llm注意力
            failures = tool_failures.get(tool_name, 0)
            count = 0
            idx = len(state.messages) - 2
            while idx >= 0 and count < failures:
                msg = state.messages[idx]
                if isinstance(msg, HumanMessage):  # 碰到用户输入说明失败记录不在本轮，停止
                    break
                if isinstance(msg, ToolMessage):
                    output.append(ToolMessage(
                        id=msg.id,
                        content=f"调用{tool_name}失败",
                        tool_call_id=msg.tool_call_id,
                        name=tool_name
                    ))
                    count += 1
                idx -= 1
            step.append(f"use tool:{tool_name} succeeded")
            tool_failures[tool_name] = 0  # 重置或保持，看你的业务逻辑
            # 【自定义事件】实时通知前端：调用成功，并带上结果内容
            _emit_tool_status(
                toolstatusEvent(status=settings.tool_success, tool_name=tool_name, args=tool_args, result=toolresult,session_id=config.get("configurable", {}).get("thread_id"),user_prompt=state.input)
            )
        else:
            step.append(f"use tool:{tool_name} failed")
            if tool_failures.get(tool_name, 0) >= max_retry_time:
                #尝试覆盖之前的所有出错消息，保持llm注意力
                count = 0
                idx = len(state.messages) - 2
                while idx >= 0 and count < tool_failures.get(tool_name, 0):
                    old_message = state.messages[idx]
                    if isinstance(old_message, HumanMessage) :
                        # 碰到用户输入说明失败记录不在本轮，停止
                        break
                    if isinstance(old_message, ToolMessage) and old_message.name== tool_name:  # ← 关键修复：只覆盖 Tool 消息
                        output.append(ToolMessage(
                            id=old_message.id,
                            content=f"调用{tool_name}失败",
                            tool_call_id=old_message.tool_call_id,
                            name=old_message.name
                        ))
                        count += 1
                    idx -= 1
                # output.append(ToolMessage(
                #     id=state.messages[-1].id,
                #     content=f"{tool_name}已经尝试调用{max_retry_time}次，皆未返回正确结果，为防止死循环，已经停止使用，请根据现有信息进行下一步操作，或者如实反馈情况",
                #     tool_call_id=tool_call_id,
                #     name=tool_name
                # ))
                info=f"\n[system Info]   {tool_name}已经尝试调用{max_retry_time}次，皆未返回正确结果，为防止死循环，已经停止使用，请根据现有信息进行下一步操作，或者如实反馈情况"
                toolresult_for_llm.error=toolresult_for_llm.error or "" + info
                _emit_tool_status(
                    toolstatusEvent(status=settings.tool_failed, tool_name=tool_name, args=None, user_prompt=state.input, result=None,session_id=config.get("configurable", {}).get("thread_id"))
                )
                tool_failures[tool_name] = 0  # 重置或保持，看你的业务逻辑
            else:
                tool_failures[tool_name] = tool_failures.get(tool_name, 0) + 1
        output.append(ToolMessage(content=toolresult_for_llm.content if toolresult_for_llm.content else toolresult_for_llm.error if toolresult_for_llm.error else toolresult_for_llm.message, tool_call_id=tool_call_id, name=tool_name))

    # ================= 4. 返回 State 更新 =================
    # 这里的 return 会持久化到 Checkpointer (SQLite) 中，供 LLM 下一步读取
    return {
        "messages": output,
        "steps": step,
        "tool_call_count": tool_failures
    }



def _emit_tool_status(event: toolstatusEvent):
    """
    安全地发送工具状态事件。
    使用 try/except 兜底，防止在非图上下文（如单元测试）中调用 get_stream_writer 导致崩溃。
    """
    try:
        writer = get_stream_writer()
        # 直接传递对象，下游 chunk 就是 toolstatusEvent 实例
        writer(event)
    except Exception as e:
        logger.warning(f"无法发送工具状态事件: {e}")








"""
使用AST结构化文件读取结果，方便降级工具调用结果（仅针对于全文读取）
"""
async def _compress_read_result(file_path: str) -> str:
    engine = UnifiedAnalysisEngine()
    request = AnalysisRequest(
        file_path=file_path,
        include_details=False,  # 摘要不需要详细属性
        include_complexity=False,
    )
    result = await engine.analyze(request)
    if not result.success:
        return f"[{file_path}: 解析失败 - {result.error_message}]"

    lines = [f"[{file_path} 共 {result.line_count} 行]"]

    for elem in result.elements:
        lines.append(f"signature: {elem.raw_text.split('\n')[0]}")
        if elem.element_type == "function":
            # 提取函数名、行号范围，可进一步从 raw_text 提取签名
            lines.append(f"  def {elem.name} L{elem.start_line}-L{elem.end_line}")
        elif elem.element_type == "class":
            lines.append(f"class {elem.name} L{elem.start_line}-L{elem.end_line}")
        elif elem.element_type == "variable" and elem.is_constant:
            lines.append(f"  const {elem.name} L{elem.start_line}-L{elem.end_line}")
        elif elem.element_type == "import":
            lines.append(f"  import {elem.name} L{elem.start_line}-L{elem.end_line}")

    return "\n".join(lines)
