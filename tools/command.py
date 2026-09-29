import shutil

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from config.data import settings
from core.toolResult import toolResult
from utils.commandSafe import truncate_output, smart_decode
from utils.errormanagerTool import compress_error
from utils.filePathTools import relativePathToAbsolute
import os
import subprocess
import re
import shlex
from pathlib import Path


INTERPRETERS = {
    ".py": "python {file}",
    ".js": "node {file}",
    ".ts": "npx --yes ts-node {file}",           # ★ 加 --yes
    ".sh": "bash -e {file}",                     # ★ 加 -e（可选）
    ".rb": "ruby {file}",
    ".go": "go run {file}",
    ".java": "java {file}",
    ".php": "php {file}",
    ".ps1": 'powershell -NoProfile -ExecutionPolicy Bypass -File "{file}"',  # ★ 加引号和参数
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




def _resolve_cwd(cwd: str, config: RunnableConfig) -> str:
    """把工具参数里的相对路径解析成绝对路径（解析失败保留原值）"""
    try:
        return str(relativePathToAbsolute(cwd, config))
    except Exception:
        return cwd



def _run_bash(command: str, abs_cwd: str, time_out: int,
               stdin_input: str | None, tool_name: str) -> toolResult:
    """在 Git Bash 下执行命令，返回结构化结果"""
    try:
        # 0. 定位 Git Bash
        bash_path = settings.GIT_BASH_PATH
        if not bash_path:
            return toolResult(
                success=False,
                content="",
                error="未找到 Git Bash (bash.exe)，请确认已安装 Git for Windows 或将 <Git>\\bin 加入 PATH",
                tool_name=tool_name
            )

        # 1. 动态决定是否需要 stdin 管道
        stdin_arg = subprocess.PIPE if stdin_input is not None else None

        # 2. UTF-8 友好的环境变量
        #    Git Bash 本身就是 UTF-8 环境，这里主要是给 Python/Node 等子进程兜底
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        env["LANG"] = "C.UTF-8"
        env["LC_ALL"] = "C.UTF-8"

        # 3. 用 bash -c 执行命令
        #    注意：shell=False，直接调用 bash.exe，避免被 cmd 再包一层
        proc = subprocess.Popen(
            [bash_path, "-lc", command],
            shell=False,
            cwd=abs_cwd,
            stdin=stdin_arg,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )

        try:
            stdout_b, stderr_b = proc.communicate(
                input=stdin_input.encode("utf-8") if stdin_input is not None else None,
                timeout=time_out
            )
        except subprocess.TimeoutExpired:
            # 超时：终止整棵进程树
            #   bash 是父进程，taskkill /T 会连带杀掉它 fork 出来的子进程
            if os.name == "nt":
                subprocess.run(
                    f"taskkill /F /T /PID {proc.pid}",
                    shell=True,
                    capture_output=True,
                )
            try:
                proc.kill()
            except Exception:
                pass
            return toolResult(
                success=False,
                content="",
                message=f"命令执行超时({time_out}秒)，已强制终止",
                tool_name=tool_name
            )

        # 4. 解码输出（Git Bash 里基本是 UTF-8，smart_decode 仍能兜底意外字节）
        stdout = truncate_output(smart_decode(stdout_b))
        stderr = truncate_output(smart_decode(stderr_b))

        final_content = ""
        if stdout:
            final_content += f"--- 标准输出 (STDOUT) ---\n{stdout}\n"
        if stderr:
            final_content += f"--- 错误输出 (STDERR) ---\n{stderr}\n"

        if not final_content:
            final_content = "命令执行完毕，无标准输出和错误输出。"

        return toolResult(
            success=(proc.returncode == 0),
            message=f"命令退出码:{proc.returncode}",
            content=final_content.strip(),
            tool_name=tool_name
        )

    except Exception as e:
        return toolResult(
            success=False,
            content="",
            error=f"命令执行失败：{compress_error(str(e))}。请检查参数或跳过此步骤，建议如实告知用户",
            tool_name=tool_name
        )

@tool(args_schema=ExecuteCommandInput)
def execute_command(command: str, cwd: str, config: RunnableConfig, time_out: int = settings.COMMAND_TIMEOUT, stdin_input: str = None) -> toolResult:
    """
      在 Git Bash 中执行一条 shell 命令并返回结果。
      用于执行**现成的命令**：运行测试、编译构建、查目录、搜文件、看版本等。
      如果代码是你现写的多行脚本（需要 import、定义函数），请用 run_code。
      Returns:
          toolResult: 包含退出码、stdout、stderr。
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

    return _run_bash(command, abs_cwd, time_out, stdin_input, "execute_command")


@tool(args_schema=RunCodeInput)
def run_code(code: str, filename: str, cwd: str, config: RunnableConfig, stdin_input: str | None = None, time_out: int = settings.COMMAND_TIMEOUT) -> toolResult:
    """
    将你编写的代码写入临时文件并执行
    【核心用途】
    这是你进行"实验"的主要工具。当你需要：
      - 复现一个 bug
      - 验证一个假设
      - 测试一段逻辑
      - 编写并运行临时脚本
      - 运行 pytest / unittest
    请优先使用本工具，而不是 execute_command。
    【与 execute_command 的区别】
      - execute_command：执行已有命令或单行查询（如 `python -c "..."`、`dir`、`findstr`）。
      - run_code：写入你编写的完整脚本文件并执行。适合多行、需要 import、需要定义函数/类的实验代码。
    【典型使用模式】
      1. 写一个最小复现脚本（如 repro.py），运行，观察现象。
      2. 根据现象修改源码。
      3. 再次运行同一个 repro.py，确认现象消失。
      4. 写一个回归测试脚本，运行确认通过。
    【文件位置】
      脚本会被写入 .MiniCode/{session_id}/{filename}。
      这是临时工作目录，不会污染项目源码，可以放心创建、覆盖、删除临时脚本。
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

    relative_file = script_path.relative_to(abs_cwd).as_posix()
    cmd = template.format(file=relative_file)
    return _run_bash(cmd, abs_cwd, time_out, stdin_input, "run_code")


if __name__ == "__main__":
    print(settings.GIT_BASH_PATH)
    result=_run_bash("echo Hello World", ".", 5, None, "test")
    print(result)

