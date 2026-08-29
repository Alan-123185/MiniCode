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
            return res

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





#错误堆栈压缩函数
def compress_error(error_msg: str, max_length: int = 200) -> str:
    """
    压缩错误信息，只保留 LLM 需要的核心内容。
    """
    error_msg = str(error_msg).strip()
    lines = error_msg.split('\n')

    if len(lines) <= 3:
        # 短错误，直接返回
        return error_msg
    # 只保留最后 2 行（通常是错误类型 + 错误描述）
    # 例如：
    #   FileNotFoundError: [Errno 2] No such file or directory: '/src/main.py'
    #   PermissionError: [Errno 13] Permission denied: '/etc/config'
    core_error = '\n'.join(lines[-2:])

    # 防止极端情况（最后一行特别长）
    if len(core_error) > max_length:
        core_error = core_error[:max_length] + "..."

    return core_error





#一个简陋的用户提示词压缩函数
def generate_summary(user_prompt: str) -> str:
    """提取或截断用户的 Prompt，只保留核心语义用于 UI 展示  这一版不够严谨，到时候需要更改"""
    # 1. 去除首尾空白
    prompt = user_prompt.strip()

    # 2. 如果太长（比如用户粘贴了大段代码），只取前 50 个字符
    if len(prompt) > 50:
        return prompt[:50] + "..."

    return prompt


#将老旧的·需要摘要的历史消息再次压缩一下
def trim_old_messages(messages: list[BaseMessage]) -> str:
    cleaned_history = []
    for msg in messages:
        if len(msg.content) > settings.MAX_OLD_MESSAGE_LENGTH:
            msg.content = msg.content[:settings.MAX_OLD_MESSAGE_LENGTH]+"...该条消息太长，已截断"
        cleaned_history.append(f"{msg.type}:{msg.content}")
    return "\n".join(cleaned_history)

