import json
from langchain_core.messages import ToolMessage, HumanMessage, AIMessage
from config.data import settings
import tiktoken
from langchain_core.messages import BaseMessage

from config.modelConfig import model_config


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




calibration_dict={
    "deepseek": 1.8,
    "default": 1.0,
    "claude": 1.6,
    "gemini":1.16
}

def count_tokens(messages: str | list[BaseMessage], model: str | None = None) -> int:
    if not model:
        model = model_config["value"].model
    arg = 1
    if "deepseek" in model.lower():
        arg = calibration_dict["deepseek"]
    if "claude" in model.lower() or "anthropic" in model.lower():
        arg = calibration_dict["claude"]
    if "gemini" in model.lower() or "google" in model.lower():
        arg = calibration_dict["gemini"]

    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")

    def _len(text) -> int:
        if not text:
            return 0
        return len(encoding.encode(str(text)))

    # 纯字符串直接算
    if isinstance(messages, str):
        return int(_len(messages) * arg)

    total = 0
    for msg in messages:
        content = msg.content
        if isinstance(content, str):
            total += _len(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    total += _len(json.dumps(block, ensure_ascii=False))
                else:
                    total += _len(block)
        else:
            total += _len(content)

        total += _len(msg.type)

        tool_calls = getattr(msg, "tool_calls", None)
        if tool_calls:
            for tc in tool_calls:
                total += _len(json.dumps(tc, ensure_ascii=False))

        total += 3

    return int(total * arg)