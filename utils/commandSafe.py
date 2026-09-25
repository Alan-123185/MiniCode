import re
from config.data import settings

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
    # ① 空内容直接返回
    if not text:
        return ""

    # ② 没超过预算，原样返回，不做任何改动
    if len(text) <= settings.COMMAND_MAX_CHAR_COUNT:
        return text

    # ③ 计算被省略的字符数
    omitted = len(text) - settings.COMMAND_HEAD - settings.COMMAND_TAIL

    # ④ 头 + 省略标记 + 尾
    truncated = (
        text[:settings.COMMAND_HEAD]                          # 前 3000 字符
        + f"\n\n... [中间省略 {omitted} 字符] ...\n\n"          # 省略标记
        + text[-settings.COMMAND_TAIL:]                       # 后 2500 字符
    )
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

