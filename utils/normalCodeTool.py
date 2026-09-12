import unicodedata
import re


def normalize_code(code: str) -> str:
    """
    LLM 代码匹配归一化。
    处理：零宽字符、全角/半角、中文标点、Tab/空格、行尾空白、多余空行。
    只做安全替换，不删注释、不改引号，结果可读且不会破坏代码结构。
    """
    if not isinstance(code, str):
        return code

    # 1. 零宽字符 / BOM / 不换行空格
    code = re.sub(r'[\u200b-\u200d\ufeff\u2060\u00a0]', '', code)

    # 2. NFKC：全角英数、全角符号 -> 半角
    code = unicodedata.normalize('NFKC', code)

    # 3. 中文标点 -> 英文标点
    zh_punct_map = {
        ord('，'): ',', ord('。'): '.', ord('！'): '!', ord('？'): '?',
        ord('；'): ';', ord('：'): ':', ord('“'): '"', ord('”'): '"',
        ord('‘'): "'", ord('’'): "'", ord('（'): '(', ord('）'): ')',
        ord('【'): '[', ord('】'): ']', ord('《'): '<', ord('》'): '>',
        ord('、'): ',', ord('…'): '...', ord('—'): '-', ord('–'): '-'
    }
    code = code.translate(zh_punct_map)

    # 4. 空白归一化
    code = code.replace('\t', '    ')          # Tab -> 4 空格
    code = code.replace('\r\n', '\n').replace('\r', '\n')  # 统一换行
    code = re.sub(r'[ \t]+$', '', code, flags=re.MULTILINE)  # 去行尾空格
    code = re.sub(r'\n{3,}', '\n\n', code)     # 多空行压成一个
    code = code.strip()                        # 去首尾空白

    return code



def normalize_line(lines: list[str]) -> list[str]:
    """单行归一化，绝不改变行数。"""
    ret=[]
    for line in lines:
        line = re.sub(r'[\u200b-\u200d\ufeff\u2060\u00a0]', '', line)
        line = unicodedata.normalize('NFKC', line)
        zh = {
            ord('，'): ',', ord('。'): '.', ord('！'): '!', ord('？'): '?',
            ord('；'): ';', ord('：'): ':', ord('“'): '"', ord('”'): '"',
            ord('‘'): "'", ord('’'): "'", ord('（'): '(', ord('）'): ')',
            ord('【'): '[', ord('】'): ']', ord('《'): '<', ord('》'): '>',
            ord('、'): ',', ord('…'): '...', ord('—'): '-', ord('–'): '-'
        }
        line = line.translate(zh)
        line = line.replace('\t', '    ')
        line = line.rstrip()
        ret.append(line)
        # 只去行尾，不动行首
    return ret
