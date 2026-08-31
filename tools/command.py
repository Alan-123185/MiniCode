from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from config.data import settings
from core.toolResult import toolResult
from utils.MessageTool import compress_error
from utils.filePathTools import relativePathToAbsolute
import os
import subprocess

@tool
def run_command(command: str, cwd: str, config:RunnableConfig , stdin_input: str = None) -> toolResult:
    """
    在终端中执行 shell 命令。
    当你修改了代码后，强烈建议使用此工具来运行测试或者编译命令。
    如果目标脚本需要交互式输入（如 Python 的 input()），请将需要输入的文本传给 stdin_input 参数。

    :param command: 要执行的命令。
    :param cwd: 命令执行的工作目录的相对路径或绝对路径。
    :param stdin_input: 可选。如果命令需要标准输入（stdin），请传入需要输入的文本。
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
            tool_name="baidu_search"
        )

    try:
        # 2. 动态决定是否需要 stdin 管道 (确保向后兼容)
        # 如果 stdin_input 为 None，则 stdin 为 None（保持默认行为，和原来完全一样）
        # 如果 stdin_input 有值，则 stdin 为 PIPE（准备接收输入）
        stdin_arg = subprocess.PIPE if stdin_input is not None else None

        proc = subprocess.Popen(
            command,
            shell=True,
            cwd=abs_cwd,
            stdin=stdin_arg,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",  # ✅ 新增：强制指定用 UTF-8 解码
            errors="replace"  # ✅ 新增：遇到解不开的字节，用 '?' 替代，防止崩溃
        )

        try:
            # 3. 将 stdin_input 传给 communicate
            # 如果 stdin_input 是 None，communicate 会忽略 input，行为和原来一致
            stdout, stderr = proc.communicate(
                input=stdin_input,
                timeout=settings.COMMAND_TIMEOUT
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
                message=f"命令执行超时({settings.COMMAND_TIMEOUT}秒),已强制终止",
                tool_name = "baidu_search"
            )

        # 4. 核心修复：使用 `or ""` 兜底，防止 stdout/stderr 为 None 导致 Pydantic 报错
        return toolResult(
            success=(proc.returncode == 0),
            content=stdout or "",
            message=stderr or "",
            tool_name="baidu_search"
        )

    except Exception as e:
        # 5. 优化异常捕获：兜底所有未知错误，防止 Agent 节点直接崩溃
        return toolResult(
            success=False,
            content="",
            error=f"命令执行失败：{compress_error(str(e))}。请检查参数或跳过此步骤，建议如实告知用户",
            tool_name="baidu_search"
        )