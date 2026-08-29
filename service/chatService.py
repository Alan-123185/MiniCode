import uuid

from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from config.chatConfig import chat_config
from config.data import Settings, settings
from config.dependencies import create_chat_config
from config.sessionManager import sessionmanager
from core.InterruptResult import InterruptResult
from mappercommon.FileOperation import FileOperation
from mappercommon.Session import Session
from mappercommon.operationGroup import OperationGroup
from requestcommon.chatRequest import ChatRequest
from requestcommon.decisionRequst import decisionRequst
from typing import AsyncGenerator

from utils.MessageTool import generate_summary


class ChatService:
    def __init__(self,graph,chat_config,sessionMapper,fileMapper,operationgroupMapper):
        self.graph=graph
        self.config=chat_config
        self.sessionMapper = sessionMapper
        self.fileMapper = fileMapper
        self.operationgroupMapper = operationgroupMapper

#改为流式的chat
    """
    前端传入会话ID，后端直接从数据库拿取信息
    """
    async def chat(self, chat_request: ChatRequest) -> AsyncGenerator[InterruptResult, None]:
        final_result = None
        config: RunnableConfig = create_chat_config(thread_id=chat_request.session_id)

        # 使用 astream 异步流式执行
        async for mode, chunk in self.graph.astream(
                {"input": chat_request.message},
                config=config,
                stream_mode=["updates", "custom"]
        ):
            if mode == "custom":
                    yield InterruptResult(message=chunk,type=settings.interrupt_type_info)

            elif mode == "updates":
                # 提取最终节点的输出
                if "output_node" in chunk:
                    final_result = chunk["output_node"].get("agentResult")

        # 流结束后，检查是否处于中断状态
        snapshot = await self.graph.aget_state(config)
        if snapshot.next:
            # ✅ 安全地获取 interrupt 信息
            interrupt_message = None
            if snapshot.tasks and snapshot.tasks[0].interrupts:
                interrupt_message = snapshot.tasks[0].interrupts[0].value
            yield InterruptResult(message=str(interrupt_message),type=settings.interrupt_type_approve)
        else:
            yield InterruptResult(agentResult=final_result,type=settings.interrupt_type_result)

    async def approve(self, decision_request: decisionRequst) -> AsyncGenerator[InterruptResult, None]:
        """用户审批结果，从暂停处恢复图继续执行"""
        config = create_chat_config(thread_id=decision_request.session_id)
        final_result = None

        async for mode, chunk in self.graph.astream(
                Command(resume=decision_request.decision),
                config=config,
                stream_mode=["updates", "custom"]
        ):
            operation_group_id=None

            if mode == "custom":
                if chunk.status == settings.tool_success and chunk.tool_name in settings.file_change_tool_list:
                    if operation_group_id is None:
                        operation_group_id = str(uuid.uuid4())
                        self.operationgroupMapper.add_operation_group(
                            OperationGroup(
                                group_id=operation_group_id,
                                session_id=chunk.session_id,
                                user_prompt=generate_summary(chunk.user_prompt),
                            )
                        )
                    fo=None
                    if chunk.tool_name == "file_edit":
                        fo = FileOperation(
                            group_id=operation_group_id,
                            file_path=chunk.args["file_path"],
                            operation_type="create_file",
                            start_line=chunk.args["start_line"],
                            end_line=chunk.args["end_line"],
                            old_snippet=chunk.result["data"],
                            new_snippet=chunk.args["new_content"]
                        )
                    elif chunk.tool_name == "create_file":
                        fo = FileOperation(
                            group_id=operation_group_id,
                            file_path=chunk.args["file_path"],
                            operation_type="create_file",
                            new_snippet=chunk.args["content"]
                        )
                    elif chunk.tool_name == "delete_file":
                        fo = FileOperation(
                            group_id=operation_group_id,
                            file_path=chunk.args["file_path"],
                            operation_type="delete_file",
                            old_snippet=chunk.result["data"]
                        )
                    self.fileMapper.add_operation(fo)
                yield InterruptResult(message=chunk, type=settings.interrupt_type_info)

            elif mode == "updates":
                if "output_node" in chunk:
                    final_result = chunk["output_node"].get("agentResult")

        # 图跑完，检查是否又遇到了新的中断
        snapshot =await self.graph.aget_state(config)
        if snapshot.next:
            interrupt_message = None
            if snapshot.tasks and snapshot.tasks[0].interrupts:
                interrupt_message = snapshot.tasks[0].interrupts[0].value
            yield InterruptResult(
                message=str(interrupt_message),
                type=settings.interrupt_type_approve
            )
        else:
            yield InterruptResult(
                agentResult=final_result,
                type=settings.interrupt_type_result
            )

    def new_chat(self, chat_request: ChatRequest) -> None:
        """创建新会话：更新数据库 + 初始化 LangGraph 状态"""
        new_session=Session(session_id=chat_request.session_id, user_id=chat_request.user_id)
        self.sessionMapper.add_session(
            new_session
        )
        sessionmanager[new_session.session_id] = new_session


