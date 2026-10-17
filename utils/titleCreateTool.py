from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from loguru import logger
from config.modelConfig import model_config
from config.sessionManager import sessionmanager
from mapper.database import DataBase
from mapper.sessionMapper import sessionMapper
from prompt import title_prompt
from requestcommon.ModelRequest import ModelSetRequest


async def new_title(session_id: str, messages: str) -> None:
    """更新会话标题"""
    model = model_config["value"]
    prompt = title_prompt.TITLE_PROMPT.format(first_message=messages)
    title_message = await model.ainvoke(
        [HumanMessage(content=prompt)], reasoning_effort="none", extra_body={"enable_thinking": False}
    )
    sessionmanager.get_session(session_id).session_name = title_message.content
    db = DataBase()
    session_mapper = sessionMapper(db)
    try:
        session_mapper.update_name(session_id=session_id, name=title_message.content)
    finally:
        db.conn.close()
    logger.info(f"会话 {session_id} 的标题已更新为: {title_message.content}")


# 硬编码测试
if __name__ == "__main__":
    from config.dependencies import create_model

    model = create_model(
        ModelSetRequest(
            base_url="https://api.chat.csu.edu.cn/v1",
            api_key="sk-JsCtaPDtaGo8eSkgJRcyMETFgWc1yRYmdK0fGCrxJZ7uJpfy",
            model_name="DeepSeek",
        )
    )
    session_id = "string"
    messages = ["帮我看看这个项目，也就是你底层的脚手架，我是你的开发者"]
    prompt = title_prompt.TITLE_PROMPT.format(first_message=messages)
    title_message = model.invoke(
        [HumanMessage(content=prompt)], reasoning_effort="none", extra_body={"enable_thinking": False}
    )
    logger.info(f"会话 {session_id} 的标题已更新为: {title_message}")
