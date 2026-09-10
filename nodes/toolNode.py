from langgraph.types import interrupt
from loguru import logger
from core.InterruptInfo import InterruptInfo
from config.data import settings
from core.toolStatusEvent import toolstatusEvent
from states.OverallState import OverAllState
from tools.OriginalContentTool import get_original_content_by_compressed_content, get_original_content_by_tool_call_id
from tools.command import execute_command
from tools.file_edit import file_edit, create_file, delete_file
from tools.file_read import readfile, listfiles
from tools.baidu_search import baidu_search
from tools.file_search import search_code_by_keyword, search_file_by_keyword
from langchain_core.messages import ToolMessage, AIMessage, HumanMessage
from langchain_core.callbacks.manager import dispatch_custom_event  # 引入自定义事件
from langchain_core.runnables import RunnableConfig  # 引入 Config 类型
from tools.undo_file_edit import undo_operationgroup, query_operationgroup

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
       get_original_content_by_compressed_content
       ]
tools_need_to_confirm=["file_edit","execute_command","delete_file","create_file"]
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
        tool = tools_by_name[tool_name]

        # ================= 1. 处理需要确认的工具 =================
        if tool_name in tools_need_to_confirm:
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
                dispatch_custom_event(
                    "on_tool_status",
                    data=toolstatusEvent(status=settings.tool_refused, tool_name=tool_name, args=tool_args, result=None),
                    config=config  # 必须传入 config，LangGraph 才知道这个事件属于哪个 thread
                )

                output.append(ToolMessage(
                    content=f"用户拒绝了 {tool_name} 的调用,请如实告知用户,如果任务无法进行,可以自行决定是否继续",
                    tool_call_id=tool_call_id
                ))
                step.append(f"user refused tool:{tool_name}")
                continue

        # ================= 2. 执行工具 =================
        step.append(f"try to use tool:{tool_name}")

        # 【自定义事件】实时通知前端：开始尝试调用
        dispatch_custom_event(
             "on_tool_status",
            data=toolstatusEvent(status=settings.tool_try, tool_name=tool_name, args=tool_args, result=None),
            config=config
        )

        toolresult = await tool.ainvoke(tool_args,config=config)
        logger.info(str(toolresult))

        # ================= 3. 处理执行结果 =================
        if toolresult.success:
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
                    ))
                    count += 1
                idx -= 1
            step.append(f"use tool:{tool_name} succeeded")
            tool_failures[tool_name] = 0  # 重置或保持，看你的业务逻辑
            # 【自定义事件】实时通知前端：调用成功，并带上结果内容
            dispatch_custom_event(
                "on_tool_status",
                data=toolstatusEvent(status=settings.tool_success, tool_name=tool_name, args=tool_args, result=toolresult),
                config=config
            )
            #这里为了节约token，还是把旧内容置空
            if tool_name=="file_edit" or tool_name=="delete_file":
                toolresult.data=None
        else:
            step.append(f"use tool:{tool_name} failed")
            logger.info(str(toolresult))
            if tool_failures.get(tool_name, 0) >= max_retry_time:
                #尝试覆盖之前的所有出错消息，保持llm注意力
                for i in range(2,max_retry_time*2-1,1):
                    old_message=state.messages[-i]
                    if isinstance(old_message, HumanMessage) :
                        break
                    output.append(ToolMessage(
                        id=old_message.id,
                        content=f"调用{tool_name}失败",
                        tool_call_id=old_message.tool_call_id
                    )
                    )
                output.append(ToolMessage(
                    content=f"{tool_name}已经尝试调用{max_retry_time}次，皆未返回正确结果，为防止死循环，已经停止使用，请根据现有信息进行下一步操作，或者如实反馈情况",
                    tool_call_id=tool_call_id
                ))
                dispatch_custom_event(
                    "on_tool_status",
                        data=toolstatusEvent(status=settings.tool_failed, tool_name=tool_name, args=None, user_prompt=state.input, result=None),
                        config=config
                    )
                tool_failures[tool_name] = 0  # 重置或保持，看你的业务逻辑
            else:
                tool_failures[tool_name] = tool_failures.get(tool_name, 0) + 1
        output.append(ToolMessage(content=toolresult.model_dump_json(), tool_call_id=tool_call_id))

    # ================= 4. 返回 State 更新 =================
    # 这里的 return 会持久化到 Checkpointer (SQLite) 中，供 LLM 下一步读取
    return {
        "messages": output,
        "steps": step,
        "tool_call_count": tool_failures
    }