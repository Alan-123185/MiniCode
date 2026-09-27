import re

from tree_sitter_analyzer.models import AnalysisResult

def build_folded_source(result: AnalysisResult, source: str) -> str:
    """把源码压成骨架：保留 imports/变量/类头/签名/docstring，折叠函数体。"""

    def _signature_line_count(raw_text: str) -> int:
        """估算签名占几行：从第一行到第一个以 ':' 结尾的物理行。"""
        for idx, line in enumerate(raw_text.splitlines()):
            if line.rstrip().endswith(":"):
                return idx + 1
        return 1

    def _indent_of(line: str) -> str:
        return line[: len(line) - len(line.lstrip())]

    def _collapse_blank_lines(text: str, max_blank: int = 1) -> str:
        # 把连续 3+ 个空行压成 max_blank 个
        return re.sub(r"\n{%d,}" % (max_blank + 1), "\n" * (max_blank + 1), text)

    lines = source.splitlines()
    total = len(lines)

    # 1. 收集所有要折叠的函数体区间 [body_start, body_end]
    folds = []          # (body_start, body_end, elem)
    for elem in result.elements or []:
        if elem.element_type not in ("function", "method"):
            continue
        raw = elem.raw_text or ""
        sig_len = _signature_line_count(raw)          # 签名占几行
        sig_end_line = elem.start_line + sig_len - 1
        body_start = sig_end_line + 1
        body_end = elem.end_line
        if body_end >= body_start:                    # 空 body 不折
            folds.append((body_start, body_end, elem))

    fold_by_start = {f[0]: f for f in folds}

    # 2. 按行扫描输出
    out = []
    i = 1
    while i <= total:
        if i in fold_by_start:
            body_start, body_end, elem = fold_by_start[i]
            indent = _indent_of(lines[body_start - 1]) if body_start <= total else "    "
            if getattr(elem, "docstring", None):
                doc = elem.docstring.strip().splitlines()[0][:120]
                out.append(f'{indent}"""{doc}"""')
            out.append(
                f"{indent}... # Implementation hidden (lines {body_start}-{body_end}), "
                f"use readfile with range to view"
            )
            i = body_end + 1
        else:
            out.append(lines[i - 1])
            i += 1

    return _collapse_blank_lines("\n".join(out))


