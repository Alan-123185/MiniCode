from langchain_core.messages import SystemMessage
from loguru import logger
from config.modelConfig import model_config
from config.sessionManager import sessionmanager
from mapper.database import DataBase
from mapper.sessionMapper import sessionMapper
from prompt import title_prompt

async def new_title(session_id: str, messages: list[str]) -> None:
    """更新会话标题"""
    model = model_config["value"]
    model.extra_body = {"enable_thinking": False}
    prompt=title_prompt.TITLE_PROMPT.format(first_message=messages)
    title =await model.ainvoke(SystemMessage(content=prompt))
    sessionmanager[session_id].session_name = title
    db = DataBase()
    session_mapper = sessionMapper(db)
    try:
        session_mapper.update_name(session_id=session_id, name=title)
    finally:
        db.conn.close()
    logger.info(f"会话 {session_id} 的标题已更新为: {title}")


