from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from config.chatConfig import chat_config
from config.dependencies import create_chat_config
from mappercommon.Session import Session
from states.OverallState import OverAllState


class sessionService:

    def __init__(self, graph,fileMapper,sessionMapper) -> None:
        self.fileMapper = fileMapper
        self.sessionMapper = sessionMapper
        self.graph = graph


    async def get_history(self, session_id: str) -> list[BaseMessage]:
        config = create_chat_config(thread_id=session_id)
        chat_config["value"] = config
        # 直接用 graph 获取最新状态
        state = await self.graph.aget_state(config)
        if not state:
            return []
        state_values = state.values or {}
        state_model = OverAllState.model_validate(state_values)
        messages = state_model.messages or []
        res = []
        for msg in messages:
            if isinstance(msg, HumanMessage) or (isinstance(msg, AIMessage) and not msg.tool_calls):
                res.append(msg)
        return res


    async def delete_chat(self, session_id: str) -> None:
        await self.graph.checkpointer.adelete_thread(session_id)
        self.sessionMapper.delete_session(session_id)
        self.fileMapper.delete_operation_by_session(session_id)


    def list_session(self,user_id) -> list[Session]:
        return self.sessionMapper.query_session_by_user_id(user_id=user_id)

    def update_name(self,session_id:str,name:str) -> None:
        self.sessionMapper.update_name(session_id=session_id,name=name)










