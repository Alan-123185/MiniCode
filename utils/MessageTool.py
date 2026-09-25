from langchain_core.messages import ToolMessage, HumanMessage, AIMessage
from config.data import settings
import tiktoken
from langchain_core.messages import BaseMessage




#一个简陋的滑动窗口函数，维持最大长度上文
def trim_message(message:list[BaseMessage]) -> int:
    count=0
    length = len(message)
    for i in range(length-1,-1,-1):
        count+=count_tokens([message[i]])
        if count>=settings.LLM_MAX_UP_MESSAGE_TOKEN:
            res=i
            while isinstance(message[res], ToolMessage):
                res-=1
            return res if res>=0 else 0

    return 0


#token计算函数
def count_tokens(messages: list[BaseMessage], model: str = settings.DEFAULT_MODEL) -> int:
    """计算 LangGraph state['messages'] 的总 token 数"""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")

    total = 0
    for msg in messages:
        # 1. 消息内容
        total += len(encoding.encode(msg.content))

        # 2. 角色名（user/assistant/system）也占 token
        role = msg.type
        total += len(encoding.encode(role))

        # 3. 如果有 tool_calls，也要算进去
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                total += len(encoding.encode(str(tc)))

        # 4. OpenAI 每条消息的固定开销
        total += 3

    return total






