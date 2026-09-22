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