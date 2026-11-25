"""文件编辑工具的测试。

file_edit / create_file / delete_file 是三个会真正落盘的工具，它们共用一套
「内容锚定 + 多级模糊匹配 + 语法检查回滚」的逻辑，所以这里围绕这套机制来做
覆盖，重点在**失败路径不能破坏文件**。

注入方式：这些工具只依赖 session.workplace 来拼路径，而 get_session 先查
sessionmanager 缓存（config/dependencies.py），所以测试里直接往缓存塞一条
会话就能绕过 DataBase / SQLite，不需要 mock。

对应实现：utils/editFileTools.py
"""

import pytest

from config.sessionManager import sessionmanager
from mappercommon.Session import Session
from utils.editFileTools import create_file_tool, delete_file_tool, file_edit_tool


@pytest.fixture
def wp(tmp_path):
    """把会话挂到临时目录；get_session 命中缓存，不会碰数据库。"""
    sessionmanager.add_session("t", Session(session_id="t", user_id="u", workplace=str(tmp_path)))
    return tmp_path


@pytest.fixture
def cfg():
    return {"configurable": {"thread_id": "t"}}


def _write(wp, name: str, text: str):
    # newline="" 保证不把 \n 转成 \r\n，否则会意外走进 CRLF 分支
    with open(wp / name, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def _read(wp, name: str) -> str:
    with open(wp / name, "r", encoding="utf-8", newline="") as f:
        return f.read()


# ---------- 精确匹配：主干路径 ----------


def test_唯一片段精确替换成功(wp, cfg):
    _write(wp, "a.py", "def f():\n    return 3\n")

    res = file_edit_tool("a.py", "    return 3\n", "    return 4\n", cfg)

    assert res.success is True
    assert _read(wp, "a.py") == "def f():\n    return 4\n"
    assert res.content  # 应当带出 diff


def test_新内容为空串即删除该片段(wp, cfg):
    """docstring 承诺：new_content 传 \"\" 表示删除匹配内容。"""
    _write(wp, "d.txt", "keep1\nremove me\nkeep2\n")

    res = file_edit_tool("d.txt", "remove me\n", "", cfg)

    assert res.success is True
    assert _read(wp, "d.txt") == "keep1\nkeep2\n"


# ---------- 精确匹配命中多处：必须拒绝且不动文件 ----------


def test_旧内容出现多次则拒绝且不改动文件(wp, cfg):
    original = "x = 1\nfoo()\nbar()\nfoo()\n"
    _write(wp, "a.py", original)

    res = file_edit_tool("a.py", "foo()\n", "baz()\n", cfg)

    assert res.success is False
    assert "多次" in res.error
    # 拒绝时磁盘必须保持原样
    assert _read(wp, "a.py") == original


# ---------- 归一化匹配（第 2 级）与相似度参考 ----------


def test_缩进用Tab也能匹配到四空格的行(wp, cfg):
    """第 2 级归一化会把 Tab 折成 4 空格，让 LLM 的缩进猜错不至于直接失败。

    断言必须是全文比对：第 2 级是「归一化后找位置、再把结果写回去」，一旦
    写回时用了归一化过的行（每行 rstrip 掉了换行），整个文件会被压成一行。
    只断言 "return 4" in 内容 的话，被压扁的 'def f():    return 4\\n'
    同样满足，测试会绿着放过这个 bug。
    """
    _write(wp, "n.py", "def f():\n    return 3\n")

    res = file_edit_tool("n.py", "\treturn 3\n", "    return 4\n", cfg)

    assert res.success is True
    assert _read(wp, "n.py") == "def f():\n    return 4\n"


def test_多行文件走归一化时保留原有换行(wp, cfg):
    """单行场景看不出问题，多行才暴露：归一化行写回会把换行全吃掉。"""
    original = "def f():\n    return 3\n\n\ndef g():\n    return 4\n"
    _write(wp, "n.py", original)

    res = file_edit_tool("n.py", "\treturn 3\n", "    return 33\n", cfg)

    assert res.success is True
    assert _read(wp, "n.py") == "def f():\n    return 33\n\n\ndef g():\n    return 4\n"


def test_相似但未达标时给出相似内容供参考(wp, cfg):
    """ratio 落在 min_hold~thread_hold 之间：不替换，但把候选片段回给模型。"""
    _write(wp, "n.txt", "a\nb\nc\n")

    res = file_edit_tool("n.txt", "a\nX\nc\n", "a\nY\nc\n", cfg)

    assert res.success is False
    assert "相似内容供参考" in res.error
    assert _read(wp, "n.txt") == "a\nb\nc\n"


def test_完全不匹配时报未找到(wp, cfg):
    _write(wp, "n.txt", "a\nb\nc\n")

    res = file_edit_tool("n.txt", "zzz\nyyy\nxxx\n", "q\n", cfg)

    assert res.success is False
    assert "未找到旧内容" in res.error
    assert _read(wp, "n.txt") == "a\nb\nc\n"


# ---------- 语法检查回滚：失败路径不能把文件改坏 ----------


def test_替换后语法出错则回滚为原文(wp, cfg):
    """把右括号删掉会让括号不闭合 -> tree_sitter 报错 -> 必须回滚。

    这里同时钉住回滚的实现方式：早先用「把新内容 replace 回旧内容」来还原，
    在 new_content 为空串时会往文件头插入字符，导致回滚结果不是原文。
    """
    original = "x = foo(\n    a,\n)\n"
    _write(wp, "a.py", original)

    res = file_edit_tool("a.py", ")\n", "", cfg)

    assert res.success is False
    assert "出现错误" in res.error
    assert _read(wp, "a.py") == original


# ---------- CRLF 文件 ----------


def test_CRLF文件用LF风格的片段也能匹配(wp, cfg):
    """读文件用 newline=""，CRLF 会原样保留；传进来的 LF 片段需被转成 CRLF。"""
    _write(wp, "c.txt", "line1\r\nline2\r\nline3\r\n")

    res = file_edit_tool("c.txt", "line2\n", "LINE2\n", cfg)

    assert res.success is True
    assert _read(wp, "c.txt") == "line1\r\nLINE2\r\nline3\r\n"


# ---------- 路径防护 ----------


def test_文件不存在时提示改用create_file(wp, cfg):
    res = file_edit_tool("nope.py", "a\n", "b\n", cfg)

    assert res.success is False
    assert "不存在" in res.error
    assert "create_file" in res.error


def test_工作目录外的绝对路径被拒绝(wp, cfg):
    outside = wp.parent / "outside.txt"
    outside.write_text("secret\n", encoding="utf-8")

    res = file_edit_tool(str(outside), "secret\n", "hacked\n", cfg)

    assert res.success is False
    assert "不在工作目录下" in res.error
    assert outside.read_text(encoding="utf-8") == "secret\n"


# ---------- create_file ----------


def test_创建新文件成功(wp, cfg):
    res = create_file_tool("i.py", "print(1)\n", cfg)

    assert res.success is True
    assert _read(wp, "i.py") == "print(1)\n"


def test_目标已存在时拒绝创建(wp, cfg):
    _write(wp, "h.txt", "x\n")

    res = create_file_tool("h.txt", "y\n", cfg)

    assert res.success is False
    assert "已存在" in res.message
    assert _read(wp, "h.txt") == "x\n"


def test_创建内容有语法错误则报错(wp, cfg):
    res = create_file_tool("bad.py", "def f(:\n    pass\n", cfg)

    assert res.success is False
    assert "语法错误" in res.error


# ---------- delete_file ----------


def test_删除文件并回传原内容(wp, cfg):
    """data 里带原内容，供 undo_operationgroup 恢复。"""
    _write(wp, "j.txt", "content to restore\n")

    res = delete_file_tool("j.txt", cfg)

    assert res.success is True
    assert (wp / "j.txt").exists() is False
    assert res.data == "content to restore\n"


def test_删除不存在的文件报错(wp, cfg):
    res = delete_file_tool("nope.txt", cfg)

    assert res.success is False
    assert "不存在" in res.error
