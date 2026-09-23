from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from config.data import settings
from core.toolResult import toolResult
from utils.MessageTool import compress_error
from utils.filePathTools import relativePathToAbsolute
import os
import subprocess
from pathlib import Path


INTERPRETERS = {
    ".py": "python {file}",
    ".js": "node {file}",
    ".ts": "npx ts-node {file}",
    ".sh": "bash {file}",
    ".rb": "ruby {file}",
    ".go": "go run {file}",
    ".java": "java {file}",  # Java 11+ 可以直接跑单文件
    ".php": "php {file}",
    ".ps1": "powershell -File {file}",
}


class ExecuteCommandInput(BaseModel):
    command: str = Field(description="要执行的命令")
    cwd: str = Field(default=".", description="命令执行的工作目录，相对路径或绝对路径，默认是 . 表示当前工作目录")
    stdin_input: str | None = Field(default=None, description="仅当命令需要交互式输入(如 input())时传入")
    time_out: int = Field(
        default=settings.COMMAND_TIMEOUT, ge=1, le=600,
        description=f"命令超时秒数，默认{settings.COMMAND_TIMEOUT}。凡 pip/npm install、编译、运行测试、下载等可能超过30秒的命令，必须传 timeout=300~600"
    )


class RunCodeInput(BaseModel):
    code: str = Field(description="要执行的代码脚本")
    filename: str = Field(description="代码文件名（包含扩展名），用于确定代码类型和执行方式")
    cwd: str = Field(default=".", description="代码执行的工作目录，相对路径或绝对路径，默认是 . 表示当前工作目录")
    stdin_input: str | None = Field(default=None, description="仅当代码需要交互式输入(如 input())时传入")
    time_out: int = Field(
        default=settings.COMMAND_TIMEOUT, ge=1, le=600,
        description=f"代码执行超时秒数，默认{settings.COMMAND_TIMEOUT}。凡 pip/npm install、编译、运行测试、下载等可能超过30秒的命令，必须传 timeout=300~600"
    )


def smart_decode(b: bytes) -> str:
    """按字节智能解码：优先UTF-8（程序输出），失败回退GBK（cmd自身错误消息），双双失败才replace"""
    if not b:
        return ""
    for enc in ("utf-8", "gbk"):
        try:
            return b.decode(enc)
        except UnicodeDecodeError:
            continue
    return b.decode("utf-8", errors="replace")


def _truncate_output(text: str) -> str:
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


def _resolve_cwd(cwd: str, config: RunnableConfig) -> str:
    """把工具参数里的相对路径解析成绝对路径（解析失败保留原值）"""
    try:
        return str(relativePathToAbsolute(cwd, config))
    except Exception:
        return cwd


def _run_shell(command: str, abs_cwd: str, time_out: int, stdin_input: str | None, tool_name: str) -> toolResult:
    """在宿主机直接执行命令（Windows 默认 cmd 环境），返回结构化结果"""
    try:
        # 1. 动态决定是否需要 stdin 管道 (确保向后兼容)
        # 如果 stdin_input 为 None，则 stdin 为 None（保持默认行为）
        # 如果 stdin_input 有值，则 stdin 为 PIPE（准备接收输入）
        stdin_arg = subprocess.PIPE if stdin_input is not None else None

        # 向子进程传递 UTF-8 环境变量，兼容 Python/Node/npm 等程序输出（UTF-8）
        # 注意：cmd 自身的错误消息（如"不是内部或外部命令"）固定按系统 OEM 代码页(GBK)写管道，
        # chcp 65001 对管道路径无效，解码交由 smart_decode 双编码尝试处理
        env = os.environ.copy()
        if os.name == "nt":
            env["PYTHONIOENCODING"] = "utf-8"
            env["PYTHONUTF8"] = "1"
            env["LANG"] = "C.UTF-8"
            env["LC_ALL"] = "C.UTF-8"

        proc = subprocess.Popen(
            command,
            shell=True,
            cwd=abs_cwd,
            stdin=stdin_arg,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env
        )

        try:
            # 2. 将 stdin_input 传给 communicate
            # 如果 stdin_input 是 None，communicate 会忽略 input，行为和原来一致
            stdout_b, stderr_b = proc.communicate(
                input=stdin_input.encode("utf-8") if stdin_input is not None else None,
                timeout=time_out
            )
        except subprocess.TimeoutExpired:
            # 超过超时时间仍在运行: 终止整棵进程树 (Windows 专属)
            subprocess.run(
                f"taskkill /F /T /PID {proc.pid}",
                shell=True,
                capture_output=True,
            )
            proc.kill()  # 确保 Python 层面的进程对象也被清理
            return toolResult(
                success=False,
                content="",
                message=f"命令执行超时({time_out}秒),已强制终止",
                tool_name=tool_name
            )

        # 3. 字节流智能解码（程序输出=UTF-8，cmd自身错误=GBK）
        stdout = _truncate_output(smart_decode(stdout_b))
        stderr = _truncate_output(smart_decode(stderr_b))

        final_content = ""
        if stdout:
            final_content += f"--- 标准输出 (STDOUT) ---\n{stdout}\n"
        if stderr:
            final_content += f"--- 错误输出 (STDERR) ---\n{stderr}\n"

        # 如果两者都为空，给个明确的提示
        if not final_content:
            final_content = "命令执行完毕，无标准输出和错误输出。"

        return toolResult(
            success=(proc.returncode == 0),
            message=f"命令退出码:{proc.returncode}",
            content=final_content.strip(),
            tool_name=tool_name
        )

    except Exception as e:
        # 4. 兜底所有未知错误，防止 Agent 节点直接崩溃
        return toolResult(
            success=False,
            content="",
            error=f"命令执行失败：{compress_error(str(e))}。请检查参数或跳过此步骤，建议如实告知用户",
            tool_name=tool_name
        )


@tool(args_schema=ExecuteCommandInput)
def execute_command(command: str, cwd: str, config: RunnableConfig, time_out: int = settings.COMMAND_TIMEOUT, stdin_input: str = None) -> toolResult:
    """
    在终端中执行 shell 命令（默认环境为 Windows cmd）。
    当你修改了代码后，强烈建议使用此工具来运行测试或者编译命令。
    Returns:
        toolResult: 命令执行结果。
    """
    # 路径转换与防御性校验 (彻底解决 WinError 267 目录无效报错)
    abs_cwd = _resolve_cwd(cwd, config)

    if not abs_cwd or not os.path.isdir(abs_cwd):
        return toolResult(
            success=False,
            content="",
            error=f"工作目录 '{abs_cwd}' 不存在或不是一个有效的目录，请检查路径是否正确。",
            tool_name="execute_command"
        )

    return _run_shell(command, abs_cwd, time_out, stdin_input, "execute_command")


@tool(args_schema=RunCodeInput)
def run_code(code: str, filename: str, cwd: str, config: RunnableConfig, stdin_input: str | None = None, time_out: int = settings.COMMAND_TIMEOUT) -> toolResult:
    """
    执行脚本并返回结构化结果，被执行的脚本文件将写入.MiniCode/{session_id}目录下
    Returns:
        toolResult: 命令执行结果。
    """
    abs_cwd = _resolve_cwd(cwd, config)

    if not abs_cwd or not os.path.isdir(abs_cwd):
        return toolResult(
            success=False,
            content="",
            error=f"工作目录 '{abs_cwd}' 不存在或不是一个有效的目录，请检查路径是否正确。",
            tool_name="run_code"
        )

    ext = Path(filename).suffix.lower()
    template = INTERPRETERS.get(ext)
    if not template:
        return toolResult(
            success=False,
            content="",
            error=f"不支持的文件类型: {ext}",
            tool_name="run_code"
        )

    # 指定路径为工作目录下的 .MiniCode/session_id/filename
    session_id = str(config.get("configurable", {}).get("thread_id") or "default")
    script_path = Path(abs_cwd) / ".MiniCode" / session_id / filename
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(code, encoding="utf-8")

    relative_file = script_path.relative_to(abs_cwd)
    cmd = f'cmd.exe /c cd /d "{abs_cwd}" && {template.format(file=str(relative_file))}'
    return _run_shell(cmd, abs_cwd, time_out, stdin_input, "run_code")
