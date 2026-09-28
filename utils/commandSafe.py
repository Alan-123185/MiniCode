
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
_ERROR_RE = re.compile(
    r"(?i)(?<![\w])(traceback|exception|error|failed|failure|fatal|panic|abort)(?![\w])"
)

# 明显不是报错的行（no errors / failed=0 / 0 errors 等）
_ERROR_NEG_RE = re.compile(
    r"(?i)(\bno\s+errors?\b|\berrors?\s*[:=]\s*0\b|\b0\s+errors?\b|\bfailed\s*[:=]\s*0\b)"
)


def _extract_error_block(
    lines: list[str],
    start: int,
    end: int,
    max_errors: int = 5,
    context: int = 2,
    max_block_lines: int = 40,
) -> str:
    """
    只在 [start, end) 区间里找报错，避免和 head/tail 重复。
    每个报错行往前/后带 context 行上下文（traceback 的 File/raise 行就在上下文中）。
    只取最后 max_errors 个报错，一般最后的才是真正致命的。
    """
    idxs = [
        i for i in range(start, end)
        if _ERROR_RE.search(lines[i]) and not _ERROR_NEG_RE.search(lines[i])
    ]
    if not idxs:
        return ""

    picked = idxs[-max_errors:]

    keep: set[int] = set()
    for i in picked:
        keep.update(range(max(start, i - context), min(end, i + context + 1)))
    keep_sorted = sorted(keep)

    # 合并连续区间，避免出现一堆零碎片段
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

    # 错误块自身也限长，否则一次刷屏又超预算
    jl = joined.splitlines()
    if len(jl) > max_block_lines:
        joined = "...\n" + "\n".join(jl[-max_block_lines:])

    return "[error]\n" + joined


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

    # 【修复 1】总行数不够头尾分：直接按字符截，并且给后缀预留长度
    if total <= head_n + tail_n:
        suffix = "\n... [输出过长，已截断]"
        limit = max(0, max_chars - len(suffix))
        return text[:limit] + suffix

    head_lines = lines[:head_n]
    tail_lines = lines[-tail_n:]
    omitted = total - head_n - tail_n  # 现在一定 >= 1，不会再是负数

    # 【修复 2】只在“中间被省略的部分”捞报错，避免和 head/tail 重复
    error_block = _extract_error_block(lines, head_n, total - tail_n)

    parts = []
    if error_block:
        parts.append(error_block)
    parts.append("\n".join(head_lines))
    parts.append(f"... [中间省略 {omitted} 行日志] ...")
    parts.append("\n".join(tail_lines))
    truncated = "\n".join(parts)

    # 【修复 3】兜底时预留后缀长度，防止最终长度 > max_chars
    if len(truncated) > max_chars:
        suffix = "\n... [超出最大字符限制，强制截断]"
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

