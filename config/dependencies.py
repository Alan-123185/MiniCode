from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from config.data import settings
from config.sessionManager import sessionmanager
from exceptions import BizException
from mapper.database import  DataBase
from mapper.sessionMapper import sessionMapper
from mappercommon.Session import Session
from prompt.llm_prompt import LLM_PROMPT
from requestcommon.ModelRequest import ModelChooseRequest

def create_chat_config(thread_id: str):
    return  {
           # "recursion_limit": settings.DEFAULT_RECURSION_LIMIT,
            "configurable": {
                "system_prompt":LLM_PROMPT,
                "thread_id": thread_id
            }
        }

def create_model(input_config:ModelChooseRequest):
    return ChatOpenAI(
        base_url=input_config.base_url,
        api_key=input_config.api_key,
        model=input_config.model_name,
        streaming=settings.DEFAULT_STREAMING_MODEL,
        stream_usage=True,  # 关键：请求流式响应中附带用量信息
        extra_body={
            "enable_thinking": True
        }
    )


def create_no_streaming_model(model:ChatOpenAI):
    return ChatOpenAI(
        base_url=model.base_url,
        api_key=model.api_key,
        model=model.model_name,
        streaming=False,
        extra_body={
            "enable_thinking": False
        }
    )



def get_session(config:RunnableConfig)-> Session:
    db=DataBase()
    sessionmapper=sessionMapper(db)
    session_id=config.get("configurable", {}).get("thread_id")
    res=sessionmanager.get(session_id, None)
    if not res:
        res=sessionmapper.query_session_by_session_id(session_id)
        if not res:
            raise BizException(message="此会话不存在")
        result=Session(
            session_id=res["id"],
            session_name=res["name"],
            workplace=res["workplace"],
            user_id=res["user_id"],
            create_time=res["created_at"]
        )
        sessionmanager[session_id]=result
        return result

    return res


def get_db():
    """
    每个请求进来时，创建一个新的数据库连接；
    请求处理完毕后，自动关闭连接，释放资源。
    """
    # 1. 创建实例（相当于 Java 里的 Mapper 对象）
    db = DataBase()

    try:
        # 2. 把 db 交给接口/Service 去使用（ yield 相当于 return，但会挂起等待）
        yield db
    finally:
        # 3. 无论接口执行成功还是报错，最后都要关掉连接（防止锁文件）
        db.conn.close()




