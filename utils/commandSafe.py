from typing import Optional

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


# 报错关键词：加词边界，避免 matched_error / error_count 之类误伤

# 假设你的 settings 已经定义
# from your_config import settings

_ERROR_RE = re.compile(
    r"(?i)(?<![\w])(traceback|exception|error|failed|failure|fatal|panic|abort)(?![\w])"
)

_ERROR_NEG_RE = re.compile(
    r"(?i)(\bno\s+errors?\b|\berrors?\s*[:=]\s*0\b|\b0\s+errors?\b|\bfailed\s*[:=]\s*0\b)"
)

# 【新增】用于排除 pytest 的假阳性状态行，例如 "test_a.py::test_b FAILED"
_PYTEST_STATUS_RE = re.compile(
    r"(?i)^\s*(FAILED|ERROR)\s+\S+::\S+|^\s*\S+::\S+\s+(FAILED|ERROR)\b"
)


def _extract_pytest_block(lines: list[str], start: int, end: int, max_lines: int = 40) -> Optional[str]:
    """
    【新增】专门提取 pytest 的 FAILURES 或 ERRORS 块。
    pytest 有明确的分隔符，直接提取比正则匹配准确 100 倍。
    """
    failure_start = -1
    failure_end = -1

    # 1. 寻找 === FAILURES === 或 === ERRORS ===
    for i in range(start, end):
        line = lines[i].strip()
        if re.match(r"^=+\s*(FAILURES|ERRORS)\s*=+$", line):
            failure_start = i
        elif failure_start != -1 and re.match(r"^=+\s*(short test summary info|ERRORS|FAILURES)\s*=+$", line):
            failure_end = i
            break

    if failure_start != -1:
        if failure_end == -1:
            failure_end = min(end, failure_start + max_lines + 10)

        block = lines[failure_start:failure_end]
        if len(block) > max_lines:
            half = max_lines // 2
            block = block[:half] + ["... [pytest output truncated] ..."] + block[-half:]

        return "[pytest errors/failures]\n" + "\n".join(block)

    # 2. 如果没有 FAILURES 块，尝试提取 short test summary info
    summary_start = -1
    for i in range(start, end):
        if re.match(r"^=+\s*short test summary info\s*=+$", lines[i].strip()):
            summary_start = i
            break

    if summary_start != -1:
        block = lines[summary_start:min(end, summary_start + 20)]
        return "[pytest summary]\n" + "\n".join(block)

    return None


def _extract_error_block(
        lines: list[str],
        start: int,
        end: int,
        max_errors: int = 5,
        context: int = 3,  # 【优化】从 2 改为 3，Python traceback 通常需要 3 行才能看懂
        max_block_lines: int = 40,
) -> str:
    """通用错误块提取（作为 pytest 特判的兜底）"""
    idxs = []
    for i in range(start, end):
        line = lines[i]
        if _ERROR_RE.search(line) and not _ERROR_NEG_RE.search(line):
            # 【优化】排除 pytest 的假阳性状态行
            if not _PYTEST_STATUS_RE.match(line):
                idxs.append(i)

    if not idxs:
        return ""

    picked = idxs[-max_errors:]

    keep: set[int] = set()
    for i in picked:
        keep.update(range(max(start, i - context), min(end, i + context + 1)))
    keep_sorted = sorted(keep)

    blocks: list[tuple[int, int]] = []
    a = prev = keep_sorted[0]
    for i in keep_sorted[1:]:
        if i == prev + 1:
            prev = i
        else:
            blocks.append((a, prev))
            a = prev = i
    blocks.append((a, prev))

    chunks = ["\n".join(lines[a:b + 1]) for a, b in blocks]
    joined = "\n...\n".join(chunks)

    jl = joined.splitlines()
    if len(jl) > max_block_lines:
        joined = "...\n" + "\n".join(jl[-max_block_lines:])

    return "[error context]\n" + joined


def truncate_output(text: str) -> str:
    if not text:
        return ""

    max_chars = settings.COMMAND_MAX_CHAR_COUNT
    if len(text) <= max_chars:
        return text

    lines = text.splitlines()
    head_n = settings.COMMAND_HEAD_LINES
    tail_n = settings.COMMAND_TAIL_LINES
    total = len(lines)

    if total <= head_n + tail_n:
        suffix = "\n... [输出过长，已截断]"
        limit = max(0, max_chars - len(suffix))
        return text[:limit] + suffix

    head_lines = lines[:head_n]
    tail_lines = lines[-tail_n:]
    omitted = total - head_n - tail_n

    # 【优化 1】优先尝试提取 Pytest 专属错误块
    error_block = _extract_pytest_block(lines, head_n, total - tail_n)

    # 【优化 2】如果没有 pytest 专属块，再使用通用正则提取
    if not error_block:
        error_block = _extract_error_block(lines, head_n, total - tail_n)

    # 【优化 3】修正拼接顺序：Head -> Error -> 省略提示 -> Tail
    parts = []
    parts.append("\n".join(head_lines))

    if error_block:
        parts.append(error_block)

    parts.append(f"\n... [system Info]中间省略 {omitted} 行日志，调用get_original_content_by_tool_call_id查看原始内容\n")
    parts.append("\n".join(tail_lines))

    truncated = "\n".join(parts)

    if len(truncated) > max_chars:
        suffix = "\n... [system Info]超出最大字符限制，强制截断，调用get_original_content_by_tool_call_id查看原始内容"
        limit = max_chars - len(suffix)
        if limit <= 0:
            return truncated[:max_chars]
        truncated = truncated[:limit] + suffix

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

