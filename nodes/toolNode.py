import asyncio
from typing import Any
from langgraph.types import interrupt
from loguru import logger
from core.InterruptInfo import InterruptInfo
from config.data import settings
from core.toolResult import toolResult
from core.toolStatusEvent import toolstatusEvent
from mappercommon.summary import Summary
from service.summaryService import summaryService
from states.OverallState import OverAllState
from langchain_core.messages import ToolMessage, HumanMessage
from langgraph.config import get_stream_writer
from langchain_core.runnables import RunnableConfig
from tools.toolManage import unsafe_tool, tools_by_name
from utils.compressMessage import _compress_read_result, _compress_execute_command_result, _compress_search_code_result
from utils.normalizeMCPresult import normalize_MCP_result
from utils.errormanagerTool import compress_error
from utils.commandSafe import is_command_safe


summary_service=summaryService()
tools_need_to_confirm=unsafe_tool()
max_retry_time=settings.MAX_TOOL_CALLS

# 注意：这里增加了 config: RunnableConfig 参数，这是触发事件的关键！
async def tool_node(state: OverAllState, config: RunnableConfig) -> OverAllState:
    tool_failures = dict(state.tool_call_count or {})
    output = []
    step = []
    last_message = state.messages[-1]
    pending_calls:list[tuple[Any,dict]] = []
    forbid_calls:list[tuple[Any,toolResult]] = []

    """
     串行处理需要确认的工具
    """

    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        tool_call_id = tool_call["id"]

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

                forbid_calls.append((tool_call, toolResult(
                  success=False, message=f"user refused tool:{tool_name}"
                )))
                step.append(f"user refused tool:{tool_name}")
                continue
        pending_calls.append((tools_by_name[tool_name], tool_call))

    """
    9.29
    改为并行执行工具
    """
    sem = asyncio.Semaphore(5)  # 限流，防止一次打爆下游

    async def _invoke(tool, tool_call_dict:dict):
        toolname = tool_call_dict["name"]
        toolargs = tool_call_dict["args"]

        _emit_tool_status(toolstatusEvent(
            status=settings.tool_try,
            tool_name=toolname,
            args=toolargs,
            result=None,
            session_id=config.get("configurable", {}).get("thread_id"),
            user_prompt=state.input,
        ))
        async with sem:
            try:
                result = await tool.ainvoke(toolargs, config=config)
                result = normalize_MCP_result(result, toolname)
                logger.info(f"调用工具 {toolname} 成功，结果: {result}")
            except Exception as e:
                logger.error(f"调用工具 {toolname} 时发生错误: {e}")
                result = toolResult(
                    success=False,
                    error=f"调用工具 {toolname} 时发生错误: {compress_error(str(e))}",
                )
        return tool_call_dict , result

    raw_results = await asyncio.gather(
        *(_invoke(tool, tc ) for tool, tc in pending_calls),
        return_exceptions=True,  # _invoke 已吞异常，这里兜底
    )
    raw_results+=forbid_calls
    #重新排序
    order = {tc["id"]: i for i, tc in enumerate(last_message.tool_calls)}
    results_sorted = sorted(
        (r for r in raw_results if not isinstance(r, BaseException)),
        key=lambda x: order.get(x[0]["id"], 0),
    )

    """
    串行处理工具调用结果，按原始顺序返回
    """

    for tool_call, toolresult in results_sorted:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        tool_call_id = tool_call["id"]
        toolresult_for_llm = toolresult

        """
        降级工具调用结果，存入summary_service，方便后续的总结节点使用        
        """
        if tool_name == "readfile":
            compress_read_content = await _compress_read_result(tool_result=toolresult, tool_call_id=tool_call_id)
            if not (compress_read_content == toolresult.error or compress_read_content == toolresult.content):
                summary_service.add_Tool_summary(Summary(
                    session_id=config.get("configurable", {}).get("thread_id"),
                    tool_call_id=tool_call_id,
                    content=toolresult.content,
                    compressed_content=compress_read_content ,
                    message_type=settings.LLM_MESSAGE_TYPE_TOOL,
                ))
        if tool_name in ("execute_command", "run_code"):
            compress_command_content=await _compress_execute_command_result(toolresult.content, tool_call_id=tool_call_id)
            if not (compress_command_content==toolresult.error or compress_command_content==toolresult.content):
                summary_service.add_Tool_summary(Summary(
                    session_id=config.get("configurable", {}).get("thread_id"),
                    tool_call_id=tool_call_id,
                    content=toolresult.content,
                    compressed_content=compress_command_content ,
                    message_type=settings.LLM_MESSAGE_TYPE_TOOL,
                ))
        if tool_name == "search_code_by_keyword":
            compress_search_content = await _compress_search_code_result(tool_result=toolresult, tool_call_id=tool_call_id)
            if not (compress_search_content == toolresult.error or compress_search_content== toolresult.content):
                summary_service.add_Tool_summary(Summary(
                    session_id=config.get("configurable", {}).get("thread_id"),
                    tool_call_id=tool_call_id,
                    content=toolresult.content,
                    compressed_content=compress_search_content,
                    message_type=settings.LLM_MESSAGE_TYPE_TOOL,
                ))
        # ================= 3. 处理执行结果 =================
        if toolresult.success:
            """
            在这里把工具调用消息就降级了，存入summary_service，方便后续的总结节点使用
            """
           # 尝试覆盖之前的所有出错消息，保持llm注意力
            failures = tool_failures.get(tool_name, 0)
            count = 0
            idx = len(state.messages) - 2
            while idx >= 0 and count < failures:
                msg = state.messages[idx]
                if isinstance(msg, HumanMessage):  # 碰到用户输入说明失败记录不在本轮，停止
                    break
                if isinstance(msg, ToolMessage) and msg.name == tool_name:  # ← 关键修复：只覆盖 Tool 消息
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







