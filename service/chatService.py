import asyncio
import uuid

from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command
from config.data import settings
from config.dependencies import create_chat_config
from config.sessionManager import sessionmanager
from core.InterruptResult import InterruptResult
from exceptions import BizException
from mappercommon.FileOperation import FileOperation
from mappercommon.Session import Session
from mappercommon.operationGroup import OperationGroup
from requestcommon.chatRequest import ChatRequest
from requestcommon.decisionRequst import decisionRequst
from typing import AsyncGenerator


class ChatService:
    def __init__(self,graph,chat_config,sessionMapper,fileMapper,operationgroupMapper):
        self.graph=graph
        self.config=chat_config
        self.sessionMapper = sessionMapper
        self.fileMapper = fileMapper
        self.operationgroupMapper = operationgroupMapper
        self.running_tasks :dict[str,asyncio.Task]= {}  # 用于跟踪每个会话的运行状态
        self.stop_flags :dict[str,asyncio.Event]= {}  # 用于标记每个会话是否需要停止运行

#改为流式的chat
    """
    前端传入会话ID，后端直接从数据库拿取信息
    """
    async def chat(self, chat_request: ChatRequest) -> AsyncGenerator[InterruptResult, None]:
        session_id = chat_request.session_id
        # 新的一轮用户交互，重置停止信号（覆盖上一次的 stop）
        self.stop_flags[session_id] = asyncio.Event()
        config = create_chat_config(thread_id=session_id)

        async for result in self._stream_graph(
                session_id=session_id,
                config=config,
                input_or_command={"input": chat_request.message},
                record_operations=False,
        ):
            yield result

    async def approve(self, decision_request: decisionRequst) -> AsyncGenerator[InterruptResult, None]:
        session_id = decision_request.session_id
        self.stop_flags[session_id] = asyncio.Event()
        config = create_chat_config(thread_id=session_id)

        async for result in self._stream_graph(
                session_id=session_id,
                config=config,
                input_or_command=Command(resume=decision_request.decision),
                record_operations=True,
        ):
            yield result

    async def _continue_chat(self, config: RunnableConfig) -> AsyncGenerator[InterruptResult, None]:
        session_id = config["configurable"]["thread_id"]
        # 注意：_continue_chat 不重置 stop_event，由上层决定
        async for result in self._stream_graph(
                session_id=session_id,
                config=config,
                input_or_command=None,
                record_operations=True,
        ):
            yield result

    async def _stream_graph(
            self,
            session_id: str,
            config: RunnableConfig,
            input_or_command,  # dict / Command / None
            record_operations: bool,  # chat 传 False，approve/_continue_chat 传 True
    ) -> AsyncGenerator[InterruptResult, None]:
        """统一的流式执行：停止检查 + 文件操作记录 + 结果汇总"""
        final_result = None
        operation_group_id = None

        stream = self.graph.astream(
            input_or_command,
            config=config,
            stream_mode=["updates", "custom"],
        )

        try:
            async for mode, chunk in stream:
                # ---- 停止检查：每个 chunk 边界 ----
                stop_event = self.stop_flags.get(session_id)
                if stop_event and stop_event.is_set():
                    yield InterruptResult(
                        message="已停止生成。",
                        type=settings.interrupt_type_info,
                    )
                    return  # 走 finally 里的 aclose

                if mode == "custom":
                    if record_operations:
                        operation_group_id = self._record_file_operation(
                            chunk, operation_group_id
                        )
                    yield InterruptResult(
                        message=chunk, type=settings.interrupt_type_info
                    )

                elif mode == "updates":
                    if "output_node" in chunk:
                        final_result = chunk["output_node"].get("agentResult")
        finally:
            # 关键：显式关闭，触发 LangGraph 内部清理与检查点落盘
            await stream.aclose()

        # ---- 流正常跑完（没被 stop），才检查是否遇到中断 ----
        snapshot = await self.graph.aget_state(create_chat_config(thread_id=session_id))
        if snapshot.next:
            interrupt_message = None
            if snapshot.tasks and snapshot.tasks[0].interrupts:
                interrupt_message = snapshot.tasks[0].interrupts[0].value
            yield InterruptResult(
                message=str(interrupt_message),
                type=settings.interrupt_type_approve,
            )
        else:
            yield InterruptResult(
                agentResult=final_result,
                type=settings.interrupt_type_result,
            )

    def _record_file_operation(self, chunk, operation_group_id):
        if chunk.status != settings.tool_success:
            return operation_group_id
        if chunk.tool_name not in settings.file_change_tool_list:
            return operation_group_id

        if operation_group_id is None:
            operation_group_id = str(uuid.uuid4())
            self.operationgroupMapper.add_operation_group(
                OperationGroup(
                    group_id=operation_group_id,
                    session_id=chunk.session_id,
                    user_prompt=generate_summary(chunk.user_prompt),
                )
            )

        if chunk.tool_name == "file_edit":
            fo = FileOperation(
                group_id=operation_group_id,
                file_path=chunk.args["file_path"],
                operation_type="file_edit",
                old_snippet=chunk.args["old_content"],
                new_snippet=chunk.args["new_content"],
            )
        elif chunk.tool_name == "create_file":
            fo = FileOperation(
                group_id=operation_group_id,
                file_path=chunk.args["file_path"],
                operation_type="create_file",
                new_snippet=chunk.args["content"],
            )
        elif chunk.tool_name == "delete_file":
            fo = FileOperation(
                group_id=operation_group_id,
                file_path=chunk.args["file_path"],
                operation_type="delete_file",
                old_snippet=chunk.result.data,
            )
        else:
            return operation_group_id

        self.fileMapper.add_operation(operation=fo)
        return operation_group_id








    def new_chat(self, chat_request: ChatRequest) -> None:
        """创建新会话：更新数据库 + 初始化 LangGraph 状态"""
        session_id = chat_request.session_id
        stop_event = asyncio.Event()
        self.stop_flags[session_id] = stop_event
        new_session=Session(session_id=chat_request.session_id, user_id=chat_request.user_id)
        self.sessionMapper.add_session(
            new_session
        )
        sessionmanager.add_session(session_id=new_session.session_id, session=new_session)


    """
    9.19
    新增后悔药功能，提升用户体验
    想要编辑重新生成消息，需要在 LangGraph 中获取当前会话的状态，找到对应的消息，然后修改其内容或替换为新的内容。
    只允许更改最远一次未造成任何影响的及其之前的消息
    
    """
    async def edit_message(self, session_id: str, message_id: str, new_content: str) -> AsyncGenerator[InterruptResult, None]:
        """编辑指定消息的内容"""
        config = create_chat_config(thread_id=session_id)
        history_list = [h async for h in self.graph.aget_state_history(config)]  # 新的在前
        if not history_list:
            yield InterruptResult(message=f"会话 {session_id} 不存在或未初始化。", type=settings.interrupt_type_info)
            return
        new_snapshot = history_list[0]
        state = new_snapshot.values
        # 查找要重新运行的消息
        index = find_safe_message_index(state["messages"])
        safe_message = state["messages"][index:]
        for i, msg in enumerate(safe_message):
            if msg.id == message_id:
                if not isinstance(msg, HumanMessage):
                    raise BizException(message=f"消息 ID {message_id} 不是用户消息，不可逆。")
                else:
                    for history in history_list:
                        if history and history.values["messages"][-1].id == message_id:
                            new_config = await self.graph.aupdate_state(history.config, {"messages": HumanMessage(content=new_content, id=message_id)})
                            run_config = create_chat_config(thread_id=session_id)
                            run_config["configurable"].update({
                                k: v for k, v in new_config["configurable"].items()
                                if k not in run_config["configurable"]  # 保留 checkpoint_ns/checkpoint_id
                            })
                            async for result in self._continue_chat(config=run_config):
                                yield result
                            return
        yield InterruptResult(message=f"消息 ID {message_id} 未找到或已被影响，无法编辑。", type=settings.interrupt_type_info)




    async def refresh_chat(self,session_id: str) -> AsyncGenerator[InterruptResult, None]:
        """从最近一个未产生异常的检查点开始执行图，用户异常恢复"""
        config = create_chat_config(thread_id=session_id)
        self.stop_flags[session_id] = asyncio.Event()
        history_list = [h async for h in self.graph.aget_state_history(config)]  # 新的在前
        if not history_list:
            yield InterruptResult(message=f"会话 {session_id} 不存在或未初始化。", type=settings.interrupt_type_info)
            return
        #把异常前的检查点作为安全点，继续执行图
        before_exception = None
        for snapshot in history_list:
            if snapshot.next:  # 有下一步说明是正常完成的检查点
                before_exception = snapshot
                break
        if not before_exception:
            yield InterruptResult(message=f"会话 {session_id} 没有可用的安全检查点，无法恢复。", type=settings.interrupt_type_info)
            return
        new_config=before_exception.config
        new_config.setdefault("configurable", {})
        new_config["configurable"]["system_prompt"] = config["configurable"]["system_prompt"]
        async for result in self._continue_chat(config=new_config):
            yield result
        return





    async def stop_chat(self, session_id: str, timeout: float = 3) -> bool:
        stop_event = self.stop_flags.get(session_id)
        if not stop_event:
            return False

        # 先走优雅路径
        stop_event.set()

        # 等 3 秒，看它自己停不停
        task = self.running_tasks.get(session_id)
        if task and not task.done():
            try:
                await asyncio.wait_for(asyncio.shield(task), timeout)
            except asyncio.TimeoutError:
                # 3 秒还没停 → 说明卡在长 await 里，强制取消
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        return True






def find_safe_message_index(messages: list[BaseMessage]) -> int:
    """
    查找最远一次未造成任何影响的消息索引。
    只有「实际执行过」（存在对应 ToolMessage 回复）的危险工具调用才算影响；
    被 interrupt 拦下、未执行的工具请求不算。
    """
    influence_function_list = ["file_edit", "execute_command", "delete_file",
                               "create_file", "undo_operationgroup"]
    # 先收集所有有 ToolMessage 回复的 tool_call_id = 真正执行过的调用
    executed_ids = {m.tool_call_id for m in messages if isinstance(m, ToolMessage)}
    for i in range(len(messages) - 1, -1, -1):
        msg = messages[i]
        if isinstance(msg, AIMessage) and any(
                tc["name"] in influence_function_list and tc["id"] in executed_ids
                for tc in (msg.tool_calls or [])):
            return i + 1
    return 0




#一个简陋的用户提示词压缩函数
def generate_summary(user_prompt: str) -> str:
    """提取或截断用户的 Prompt，只保留核心语义用于 UI 展示  这一版不够严谨，到时候需要更改"""
    # 1. 去除首尾空白
    prompt = user_prompt.strip()

    # 2. 如果太长（比如用户粘贴了大段代码），只取前 50 个字符
    if len(prompt) > 50:
        return prompt[:50] + "..."

    return prompt



    # async def chat(self, chat_request: ChatRequest) -> AsyncGenerator[InterruptResult, None]:
    #     final_result = None
    #     config: RunnableConfig = create_chat_config(thread_id=chat_request.session_id)
    #     # 使用 astream 异步流式执行
    #     async for mode, chunk in self.graph.astream(
    #             {"input": chat_request.message},
    #             config=config,
    #             stream_mode=["updates", "custom"]
    #     ):
    #         if mode == "custom":
    #                 yield InterruptResult(message=chunk,type=settings.interrupt_type_info)
    #
    #         elif mode == "updates":
    #             # 提取最终节点的输出
    #             if "output_node" in chunk:
    #                 final_result = chunk["output_node"].get("agentResult")
    #
    #     # 流结束后，检查是否处于中断状态
    #     snapshot = await self.graph.aget_state(config)
    #     if snapshot.next:
    #         # ✅ 安全地获取 interrupt 信息
    #         interrupt_message = None
    #         if snapshot.tasks and snapshot.tasks[0].interrupts:
    #             interrupt_message = snapshot.tasks[0].interrupts[0].value
    #         yield InterruptResult(message=str(interrupt_message),type=settings.interrupt_type_approve)
    #     else:
    #         yield InterruptResult(agentResult=final_result,type=settings.interrupt_type_result)
    #
    # async def approve(self, decision_request: decisionRequst) -> AsyncGenerator[InterruptResult, None]:
    #     """用户审批结果，从暂停处恢复图继续执行"""
    #     config = create_chat_config(thread_id=decision_request.session_id)
    #     final_result = None
    #     operation_group_id = None
    #     async for mode, chunk in self.graph.astream(
    #             Command(resume=decision_request.decision),
    #             config=config,
    #             stream_mode=["updates", "custom"]
    #     ):
    #         if mode == "custom":
    #             if chunk.status == settings.tool_success and chunk.tool_name in settings.file_change_tool_list:
    #                 if operation_group_id is None:
    #                     operation_group_id = str(uuid.uuid4())
    #                     self.operationgroupMapper.add_operation_group(
    #                         OperationGroup(
    #                             group_id=operation_group_id,
    #                             session_id=chunk.session_id,
    #                             user_prompt=generate_summary(chunk.user_prompt),
    #                         )
    #                     )
    #                 fo=None
    #                 if chunk.tool_name == "file_edit":
    #                     fo = FileOperation(
    #                         group_id=operation_group_id,
    #                         file_path=chunk.args["file_path"],
    #                         operation_type="file_edit",
    #                         old_snippet=chunk.args["old_content"],
    #                         new_snippet=chunk.args["new_content"]
    #                     )
    #                 elif chunk.tool_name == "create_file":
    #                     fo = FileOperation(
    #                         group_id=operation_group_id,
    #                         file_path=chunk.args["file_path"],
    #                         operation_type="create_file",
    #                         new_snippet=chunk.args["content"]
    #                     )
    #                 elif chunk.tool_name == "delete_file":
    #                     fo = FileOperation(
    #                         group_id=operation_group_id,
    #                         file_path=chunk.args["file_path"],
    #                         operation_type="delete_file",
    #                         old_snippet=chunk.result.data
    #                     )
    #                 self.fileMapper.add_operation(operation=fo)
    #             yield InterruptResult(message=chunk, type=settings.interrupt_type_info)
    #
    #         elif mode == "updates":
    #             if "output_node" in chunk:
    #                 final_result = chunk["output_node"].get("agentResult")
    #
    #     # 图跑完，检查是否又遇到了新的中断
    #     snapshot =await self.graph.aget_state(config)
    #     if snapshot.next:
    #         interrupt_message = None
    #         if snapshot.tasks and snapshot.tasks[0].interrupts:
    #             interrupt_message = snapshot.tasks[0].interrupts[0].value
    #         yield InterruptResult(
    #             message=str(interrupt_message),
    #             type=settings.interrupt_type_approve
    #         )
    #     else:
    #         yield InterruptResult(
    #             agentResult=final_result,
    #             type=settings.interrupt_type_result
    #         )
    #
    #
    #
    # async def _continue_chat(self,config:RunnableConfig) -> AsyncGenerator[InterruptResult, None]:
    #     """继续执行图，直到遇到中断或完成"""
    #     final_result = None
    #     operation_group_id = None
    #     async for mode, chunk in self.graph.astream(
    #             None,
    #             config=config,
    #             stream_mode=["updates", "custom"]
    #     ):
    #         if mode == "custom":
    #             if chunk.status == settings.tool_success and chunk.tool_name in settings.file_change_tool_list:
    #                 if operation_group_id is None:
    #                     operation_group_id = str(uuid.uuid4())
    #                     self.operationgroupMapper.add_operation_group(
    #                         OperationGroup(
    #                             group_id=operation_group_id,
    #                             session_id=chunk.session_id,
    #                             user_prompt=generate_summary(chunk.user_prompt),
    #                         )
    #                     )
    #                 fo=None
    #                 if chunk.tool_name == "file_edit":
    #                     fo = FileOperation(
    #                         group_id=operation_group_id,
    #                         file_path=chunk.args["file_path"],
    #                         operation_type="file_edit",
    #                         old_snippet=chunk.args["old_content"],
    #                         new_snippet=chunk.args["new_content"]
    #                     )
    #                 elif chunk.tool_name == "create_file":
    #                     fo = FileOperation(
    #                         group_id=operation_group_id,
    #                         file_path=chunk.args["file_path"],
    #                         operation_type="create_file",
    #                         new_snippet=chunk.args["content"]
    #                     )
    #                 elif chunk.tool_name == "delete_file":
    #                     fo = FileOperation(
    #                         group_id=operation_group_id,
    #                         file_path=chunk.args["file_path"],
    #                         operation_type="delete_file",
    #                         old_snippet=chunk.result.data
    #                     )
    #                 self.fileMapper.add_operation(operation=fo)
    #             yield InterruptResult(message=chunk, type=settings.interrupt_type_info)
    #
    #         elif mode == "updates":
    #             if "output_node" in chunk:
    #                 final_result = chunk["output_node"].get("agentResult")
    #
    #     # 图跑完，检查是否又遇到了新的中断
    #     snapshot = await self.graph.aget_state(create_chat_config(thread_id=config["configurable"]["thread_id"]))
    #     if snapshot.next:
    #         interrupt_message = None
    #         if snapshot.tasks and snapshot.tasks[0].interrupts:
    #             interrupt_message = snapshot.tasks[0].interrupts[0].value
    #         yield InterruptResult(
    #             message=str(interrupt_message),
    #             type=settings.interrupt_type_approve
    #         )
    #     else:
    #         yield InterruptResult(
    #             agentResult=final_result,
    #             type=settings.interrupt_type_result
    #         )
    #
