import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from loguru import logger

from exceptions import BizException
from mapper.database import DataBase
from mapper.modelMapper import modelMapper
from nodes.summeraizeConditionNode import summerize_condition_node
from nodes.summerizeNode import summerize_node
from nodes.toolConditionNode import tool_condition_node
from nodes.inputNode import input_node
from nodes.llmNode import llm_node
from nodes.outputNode import output_node
from nodes.toolNode import tool_node
from service.modelService import modelService
from states.InputState import InputState
from states.OverallState import OverAllState
from states.outputState import OutputState


# 1. 声明全局变量，初始为 None
graph = None
_db_conn = None
global model_service
db = DataBase()
# 2. 定义图结构 (这部分保持你原来的逻辑不变)
builder = StateGraph(
    state_schema=OverAllState,
    input_schema=InputState,
    output_schema=OutputState
)

builder.add_node("input_node", input_node)
builder.add_node("output_node", output_node)
builder.add_node("llm_node", llm_node)
builder.add_node("tool_condition_node", tool_condition_node)
builder.add_node("tool_node", tool_node)
builder.add_node("summerize_node",summerize_node)
builder.add_node("summerize_condition_node",summerize_condition_node)

builder.add_edge(START, "input_node")
builder.add_edge("output_node", END)
builder.add_edge("summerize_node", "llm_node")
builder.add_edge("tool_node", "llm_node")


builder.add_conditional_edges(
    "llm_node",
    tool_condition_node,
    {
        "tools": "tool_node",  # 需要工具跳到工具调用节点
        END: "output_node"  # 如果不需要调用工具，直接跳到输出节点
    }
)
builder.add_conditional_edges(
    "input_node",
    summerize_condition_node,
    {
        "summerize": "summerize_node", END: "llm_node" }
)

# 3. 定义异步初始化函数 (替代原来的直接编译)
async def initialize_graph():
    global graph, _db_conn
    if graph is not None:
        return  # 防止重复初始化

    logger.info("🔄 正在初始化 LangGraph 和 AsyncSqliteSaver...")

    _db_conn = await aiosqlite.connect("minicodex_checkpointer.db")  # ★ 独立文件，不再和业务库混用

    checkpointer = AsyncSqliteSaver(_db_conn)

    await checkpointer.setup()  # ★ 确保其内部表初始化（原代码从没调过，之前靠共用文件里的旧表侥幸工作）

    graph = builder.compile(checkpointer=checkpointer)
    db = DataBase()
    model_service = modelService(modelMapper(db))
    try:
        model_service.old_choose_model()
    except Exception as e:
        raise BizException(message="---------ERROR 请先选择模型----------")
    finally:
        db.conn.close()  # 确保数据库连接关闭，避免资源泄漏
    logger.info("✅ LangGraph 和 AsyncSqliteSaver 初始化成功！")


# 4. 定义清理函数
async def close_graph():
    global _db_conn
    if _db_conn:
        await _db_conn.close()
        logger.info("🛑 LangGraph 数据库连接已关闭")