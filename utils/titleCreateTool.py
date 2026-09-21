from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from loguru import logger
from config.modelConfig import model_config
from config.sessionManager import sessionmanager
from mapper.database import DataBase
from mapper.sessionMapper import sessionMapper
from prompt import title_prompt
from requestcommon.ModelRequest import ModelChooseRequest


async def new_title(session_id: str, messages: list[str]) -> None:
    """更新会话标题"""
    model = model_config["value"]
    prompt=title_prompt.TITLE_PROMPT.format(first_message=messages)
    title_message =await model.ainvoke([SystemMessage(content=prompt)],reasoning_effort="none",extra_body={"enable_thinking": False})
    sessionmanager["session"][session_id].session_name = title_message.content
    db = DataBase()
    session_mapper = sessionMapper(db)
    try:
        session_mapper.update_name(session_id=session_id, name=title_message.content)
    finally:
        db.conn.close()
    logger.info(f"会话 {session_id} 的标题已更新为: {title_message.content}")










#硬编码测试
if __name__=="__main__":
    from config.dependencies import create_model
    model=create_model(ModelChooseRequest(
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key="sk-ws-H.EXIRYMP.4Lrl.MEUCIQD21KzYKp6qoSCsYlim1IqpE9bsoAVtzY3bNNEJPdg7BQIgddUrdtJnalhHNslpul_yv0cTGrWmMeUXtvcOZ0hYfgo",
        model_name="qwen3.6-plus"
    ))
    session_id="string"
    messages=[HumanMessage(content="帮我修复一下ragdemo下的一些bug"),AIMessage(content="已完成所有修复，以下是变更总结：\n\n---\n\n### 修复的 Bug\n\n| # | 文件 | 问题 | 修复 |\n|---|------|------|------|\n| 1 | `vector_store.py` | 属性名拼写错误 `self.vector_sotre` | 改为 `self.vector_store` |\n| 2 | `rag.py` | `reverse1` 参数名 `dict` 覆盖 Python 内置类型 | 改为 `lambda x: x[\"question\"]` |\n| 3 | `rag.py` | `func` 函数对 `None` 和空列表 `[]` 的处理不一致（`answer is None` 无法捕获空列表） | 统一为 `if not answer:` 判断 |\n| 4 | `rag.py` | `func` 返回用 `''.join()` 拼接，各条检索结果之间没有分隔符 | 改为 `'\\n'.join()` |\n| 5 | `rag.py` | 存在未使用的废弃函数 `reverse0`、`reverse1`、`reverse2` | 全部删除，精简代码 |\n| 6 | `knowledge_base.py` | 列表推导式中变量名 `for i in answer` 不规范（与内置函数名冲突且语义不清） | 改为 `for _ in answer` |")]
    prompt = title_prompt.TITLE_PROMPT.format(first_message=messages)
    title_message =model.invoke([SystemMessage(content=prompt)], reasoning_effort="none")
    logger.info(f"会话 {session_id} 的标题已更新为: {title_message.content}")


