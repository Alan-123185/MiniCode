
from config.data import settings
import re


_CHAIN_SPLIT = re.compile(r"&&|\|\||\||;|&|\n|>>|>|<")   # 拆链式命令

def is_command_safe(command: str, stdin_input: str | None = None) -> bool:
    """
    判断 execute_command 的命令是否全部命中只读白名单。
    防绕过关键：按 && || | ; & 换行拆成多段，每一段都必须命中，
    'git status && del xxx' 会因第二段不匹配而照常弹确认。
    """
    if stdin_input is not None:      # 带交互输入的不放行
        return False
    patterns = [re.compile(p, re.IGNORECASE) for p in settings.SAFE_COMMAND_WHITELIST]
    segments = [s.strip() for s in _CHAIN_SPLIT.split(command) if s.strip()]
    if not segments:
        return False
    return all(any(p.match(s) for p in patterns) for s in segments)


#压缩命令行输出


def truncate_output(text: str) -> str:
    if not text:
        return ""

    # 没超过预算，原样返回
    if len(text) <= settings.COMMAND_MAX_CHAR_COUNT:
        return text

    lines = text.splitlines()

    # 【核心优化 1】：正则捞报错（忽略大小写）
    error_pattern = re.compile(r"(error|exception|traceback|failed|fatal)", re.IGNORECASE)
    error_lines = [line for line in lines if error_pattern.search(line)]

    # 如果有报错，把报错行提取出来放在最前面（最多保留 10 行，防刷屏）
    error_block = ""
    if error_lines:
        error_block = "[error]:\n" + "\n".join(error_lines[:10]) + "\n\n"

    # 【核心优化 2】：按“行”掐头去尾，而不是按字符
    # 计算头尾保留多少行（简单按字符数换算成行数，或者直接设定固定行数）
    head_lines = lines[:settings.COMMAND_HEAD_LINES]  # 比如前 50 行
    tail_lines = lines[-settings.COMMAND_TAIL_LINES:]  # 比如后 50 行

    omitted_lines = len(lines) - len(head_lines) - len(tail_lines)

    # 拼接：关键报错 + 头部 + 省略标记 + 尾部
    truncated = (
            error_block
            + "\n".join(head_lines)
            + f"\n\n... [中间省略 {omitted_lines} 行日志] ...\n\n"
            + "\n".join(tail_lines)
    )

    # 最后兜底：如果拼起来还是太长（极端情况），再按字符硬切一次
    if len(truncated) > settings.COMMAND_MAX_CHAR_COUNT:
        truncated = truncated[:settings.COMMAND_MAX_CHAR_COUNT] + "\n... [超出最大字符限制，强制截断]"

    return truncated

"""按字节智能解码：优先UTF-8（程序输出），失败回退GBK（cmd自身错误消息），双双失败才replace"""
def smart_decode(b: bytes) -> str:
    if not b:
        return ""
    for enc in ("utf-8", "gbk"):
        try:
            return b.decode(enc)
        except UnicodeDecodeError:
            continue
    return b.decode("utf-8", errors="replace")

