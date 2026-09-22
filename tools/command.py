from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from config.data import settings
from config.sessionManager import sessionmanager
from core.commandResult import commandResult
from core.toolResult import toolResult
from sandbox_executor.MXCExecutor import MxcExecutor
from utils.filePathTools import relativePathToAbsolute
import os


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



@tool(args_schema=ExecuteCommandInput)
def execute_command(command: str, cwd: str, config : RunnableConfig , time_out: int =settings.COMMAND_TIMEOUT,  stdin_input: str = None) -> toolResult:
    """
    在当前会话的 MXC 沙箱中执行各种命令并返回结构化结果。
    Returns:
        toolResult: 命令执行结果。
    """
    # 1. 路径转换与防御性校验 (彻底解决 WinError 267 目录无效报错)

    try:
        abs_cwd =relativePathToAbsolute(cwd,config)
    except Exception :
        abs_cwd = cwd  # 如果转换函数报错，保留原值

    if not abs_cwd or not os.path.isdir(abs_cwd):
        return toolResult(
            success=False,
            content="",
            error=f"工作目录 '{abs_cwd}' 不存在或不是一个有效的目录，请检查路径是否正确。",
            tool_name="execute_command"
        )
    """
    9.21
    new content! with MXCExecutor run command in sandbox
    
    """
    _executor = sessionmanager.get_executor(config.get("configurable", {}).get("thread_id"))
    if not _executor:
        _executor = MxcExecutor(mxc_path=settings.MXC_path, session_id=config.get("configurable", {}).get("thread_id"))
        sessionmanager.add_executor(session_id=config.get("configurable", {}).get("thread_id"), executor=_executor)


    command_result = _executor.run(command=command, workplace=str(abs_cwd),stdin_input=stdin_input, time_out=time_out)

    return _fresh_result(command_result) if command_result.success else toolResult(
        success=False,
        message=f"命令退出码:{command_result.exitcode}",
        error=command_result.stderr,
        tool_name="execute_command"
    )


@tool(args_schema=RunCodeInput)
def run_code(code: str, filename: str, cwd: str, config: RunnableConfig ,stdin_input: str | None = None, time_out: int = settings.COMMAND_TIMEOUT) -> toolResult:
    """
    在 MXC 沙箱中执行脚本并返回结构化结果，被执行的脚本文件将写入.MiniCode/{session_id}目录下
    Returns:
        toolResult: 命令执行结果。
    """
    try:
        abs_cwd =relativePathToAbsolute(cwd,config)
    except Exception :
        abs_cwd = cwd  # 如果转换函数报错，保留原值

    if not abs_cwd or not os.path.isdir(abs_cwd):
        return toolResult(
            success=False,
            content="",
            error=f"工作目录 '{abs_cwd}' 不存在或不是一个有效的目录，请检查路径是否正确。",
            tool_name="run_code"
        )
    _executor = sessionmanager.get_executor(config.get("configurable", {}).get("thread_id"))
    if not _executor:
        _executor = MxcExecutor(mxc_path=settings.MXC_path,session_id=config.get("configurable", {}).get("thread_id"))
        sessionmanager.add_executor(session_id=config.get("configurable", {}).get("thread_id"), executor=_executor)
    run_result=_executor.run_code(code=code, filename=filename,workplace=str(abs_cwd), stdin_input=stdin_input, time_out=time_out)
    return _fresh_result(run_result) if run_result.success else toolResult(
        success=False,
        content=f"命令退出码:{run_result.exitcode}",
        error=run_result.stderr,
        tool_name="run_code"
    )





def _fresh_result(command_result:commandResult,):
        stdout = command_result.stdout
        stderr = command_result.stderr
        code = command_result.exitcode
        final_content = ""
        if stdout:
            final_content += f"--- 标准输出 (STDOUT) ---\n{stdout}\n"
        if stderr:
            final_content += f"--- 错误输出 (STDERR) ---\n{stderr}\n"

        # 如果两者都为空，给个明确的提示
        if not final_content:
            final_content = "命令执行完毕，无标准输出和错误输出。"

        return toolResult(
            success=(code == 0),
            message=f"命令退出码:{code}",
            content=final_content.strip(),
            tool_name="execute_command"
        )












    # try:
    #     # 2. 动态决定是否需要 stdin 管道 (确保向后兼容)
    #     # 如果 stdin_input 为 None，则 stdin 为 None（保持默认行为，和原来完全一样）
    #     # 如果 stdin_input 有值，则 stdin 为 PIPE（准备接收输入）
    #     stdin_arg = subprocess.PIPE if stdin_input is not None else None
    #
    #     # 向子进程传递 UTF-8 环境变量，兼容 Python/Node/npm 等程序输出（UTF-8）
    #     # 注意：cmd 自身的错误消息（如"不是内部或外部命令"）固定按系统 OEM 代码页(GBK)写管道，
    #     # chcp 65001 对管道路径无效，解码交由 smart_decode 双编码尝试处理
    #     shell_command = command
    #     env = os.environ.copy()
    #     if os.name == "nt":
    #         env["PYTHONIOENCODING"] = "utf-8"
    #         env["PYTHONUTF8"] = "1"
    #         env["LANG"] = "C.UTF-8"
    #         env["LC_ALL"] = "C.UTF-8"
    #
    #     proc = subprocess.Popen(
    #         shell_command,
    #         shell=True,
    #         cwd=abs_cwd,
    #         stdin=stdin_arg,
    #         stdout=subprocess.PIPE,
    #         stderr=subprocess.PIPE,
    #         env=env
    #     )
    #
    #     try:
    #         # 3. 将 stdin_input 传给 communicate
    #         # 如果 stdin_input 是 None，communicate 会忽略 input，行为和原来一致
    #         stdout_b, stderr_b = proc.communicate(
    #             input=stdin_input.encode("utf-8") if stdin_input is not None else None,
    #             timeout=time_out
    #         )
    #     except subprocess.TimeoutExpired:
    #         # 超过超时时间仍在运行: 终止整棵进程树 (Windows 专属)
    #         subprocess.run(
    #             f"taskkill /F /T /PID {proc.pid}",
    #             shell=True,
    #             capture_output=True,
    #         )
    #         proc.kill()  # 确保 Python 层面的进程对象也被清理
    #         return toolResult(
    #             success=False,
    #             content="",
    #             message=f"命令执行超时({time_out}秒),已强制终止",
    #             tool_name = "execute_command"
    #         )
    # 4. 字节流智能解码（程序输出=UTF-8，cmd自身错误=GBK）