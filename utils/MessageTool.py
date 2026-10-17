import json
import os
import re

from langchain_core.messages import ToolMessage, AIMessage
from config.data import settings
from langchain_core.messages import BaseMessage


# 一个简陋的滑动窗口函数，维持最大长度上文
def trim_message(messages: list[BaseMessage]) -> int:
    limit = settings.LLM_MAX_UP_MESSAGE_TOKEN
    if context_tokens(messages) < limit:
        return 0  # 没超，不裁

    count = 0
    for i in range(len(messages) - 1, -1, -1):
        count += _message_tokens(messages[i])
        if count >= limit:
            res = i
            while res > 0 and isinstance(messages[res], ToolMessage):
                res -= 1
            return res
    return 0


# 中日韩字符及全角标点
_CJK = re.compile(r"[\u2e80-\u9fff\uac00-\ud7af\uf900-\ufaff\uff00-\uffef]")


def _estimate(text) -> int:
    """粗略估算：中日韩约 1.5 token/字，其余约 3.5 字符/token"""
    if not text:
        return 0
    text = str(text)
    # 超长文本不跑正则，直接按字符数粗算
    if len(text) > 50_000:
        return len(text) // 2
    cjk = len(_CJK.findall(text))
    return int(cjk * 1.5 + (len(text) - cjk) / 3.5) + 1


def _message_tokens(msg: BaseMessage) -> int:
    """单条消息的 token：AIMessage 优先用真实 output_tokens，其余估算"""
    um = getattr(msg, "usage_metadata", None)
    if isinstance(msg, AIMessage) and um and um.get("output_tokens"):
        out = um["output_tokens"]
        # 推理模型的思考 token 不会回传到下一轮上下文，扣掉
        reasoning = (um.get("output_token_details") or {}).get("reasoning", 0) or 0
        return max(out - reasoning, 0) + 3

    total = 3
    content = msg.content
    if isinstance(content, str):
        total += _estimate(content)
    elif isinstance(content, list):
        for block in content:
            total += _estimate(json.dumps(block, ensure_ascii=False) if isinstance(block, dict) else block)
    else:
        total += _estimate(content)

    for tc in getattr(msg, "tool_calls", None) or []:
        total += _estimate(json.dumps(tc, ensure_ascii=False))
    return total


def context_tokens(messages: list[BaseMessage]) -> int:
    """
    当前上下文总 token 数：
    最近一条带 usage 的 AIMessage 的真实总量 + 其后新增消息的估算。
    没有任何 usage 时，退化为全量估算。
    """
    for i in range(len(messages) - 1, -1, -1):
        m = messages[i]
        um = getattr(m, "usage_metadata", None)
        if isinstance(m, AIMessage) and um:
            base = (um.get("input_tokens") or 0) + (um.get("output_tokens") or 0)
            if base > 0:
                return base + sum(_message_tokens(x) for x in messages[i + 1 :])
    return sum(_message_tokens(x) for x in messages)


def count_tokens(messages: str | list[BaseMessage], model: str | None = None) -> int:
    """兼容旧签名：str 走估算，list 走逐条统计。model 已不再使用。"""
    if isinstance(messages, str):
        return _estimate(messages)
    return sum(_message_tokens(m) for m in messages)
