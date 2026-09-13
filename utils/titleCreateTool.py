from langchain_core.messages import SystemMessage
from loguru import logger
from config.modelConfig import model_config
from config.sessionManager import sessionmanager
from mapper.fileMapper import FileOperationMapper
from mapper.database import DataBase
from mapper.sessionMapper import sessionMapper
from prompt import title_prompt
from service.sessionService import sessionService
from graphs.chat_graph import graph



db=DataBase()
file_mapper=FileOperationMapper(db)
session_mapper=sessionMapper(db)
async def new_title(session_id: str, messages: list[str]) -> None:
    """更新会话标题"""
    model = model_config["value"]
    model.extra_body = {"enable_thinking": False}
    prompt=title_prompt.TITLE_PROMPT.format(first_message=messages)
    title =await model.ainvoke(SystemMessage(content=prompt))
    sessionmanager[session_id].session_name = title
    session_service = sessionService(graph=graph, fileMapper=file_mapper, sessionMapper=session_mapper)
    session_service.update_name(session_id=session_id, name=title)
    logger.info(f"会话 {session_id} 的标题已更新为: {title}")


