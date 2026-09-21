from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from config.data import settings
from config.sessionManager import sessionmanager
from core.toolResult import toolResult
from sandbox_executor.MXCExecutor import MxcExecutor
from utils.MessageTool import compress_error
from utils.filePathTools import relativePathToAbsolute
import os


class ExecuteCommandInput(BaseModel):
    command: str = Field(description="要执行的命令")
    cwd: str = Field(description="命令执行的工作目录，相对路径或绝对路径")
    stdin_input: str | None = Field(default=None, description="仅当命令需要交互式输入(如 input())时传入")
    time_out: int = Field(
        default=settings.COMMAND_TIMEOUT, ge=1, le=600,
        description=f"命令超时秒数，默认{settings.COMMAND_TIMEOUT}。凡 pip/npm install、编译、运行测试、下载等可能超过30秒的命令，必须传 timeout=300~600"
    )

@tool(args_schema=ExecuteCommandInput)
def execute_command(command: str, cwd: str, config : RunnableConfig , time_out: int =settings.COMMAND_TIMEOUT,  stdin_input: str = None) -> toolResult:
    """
    在终端中执行 shell 命令（默认环境为 Windows cmd）。
    当你修改了代码后，强烈建议使用此工具来运行测试或者编译命令。
    :return: 返回一个工具调用结果类
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
    #构造 MXCExecutor 实例，确保在沙箱中执行命令

    try:
        _executor = sessionmanager["executor"][config["configurable"]["session_id"]]
    except KeyError:
        _executor = MxcExecutor(mxc_path=settings.MXC_path, workplace=cwd)
        sessionmanager["executor"][config["configurable"]["session_id"]] = _executor

        command_result = _executor.run(command=command, stdin_input=stdin_input, time_out=time_out)
        stdout=command_result.stdout
        stderr=command_result.stderr
        code=command_result.exitcode
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

    except Exception as e:
        # 5. 优化异常捕获：兜底所有未知错误，防止 Agent 节点直接崩溃
        return toolResult(
            success=False,
            error=f"命令执行失败：{compress_error(str(e))}。请检查参数或跳过此步骤，建议如实告知用户",
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