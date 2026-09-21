import json  # 导入 json 模块，用于将 Python 对象序列化为 JSON 字符串并写入临时配置文件
import os
import subprocess  # 导入 subprocess 模块，用于启动外部进程（这里是启动沙箱二进制）
import tempfile  # 导入 tempfile 模块，用于创建临时文件（存放沙箱配置）
from pathlib import Path  # 从 pathlib 导入 Path 类，用于跨平台的路径操作
from config.data import settings
from core.commandResult import commandResult
from utils.MessageTool import compress_error

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


class MxcExecutor:
    # 这是一个封装 MXC（为某个沙箱执行器）执行相关操作的类
    def __init__(self, mxc_path: Path, workplace: str, session_id: str):
        # mxc_path: 沙箱二进制的路径（可执行文件）
        # workplace: 在沙箱中提供给进程的工作目录（以及脚本写入目录）
        self.binary = mxc_path  # 将二进制路径转换为 Path 对象，方便后续拼接和传参
        self.workplace = Path(workplace).resolve()  # 将工作目录路径解析为绝对路径并转换为 Path 对象
        self.session_id=session_id


    def run(self, command: str, time_out: int = settings.COMMAND_TIMEOUT, stdin_input: str = None) -> commandResult:
        # 1. 构建沙箱配置，time_out 是秒，配置里用毫秒
        config = self._build_config(command, time_out=time_out)
        with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", encoding="utf-8", delete=False
        ) as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
            config_path = f.name

        try:
            env = os.environ.copy()
            if os.name == "nt":
                env["PYTHONIOENCODING"] = "utf-8"
                env["PYTHONUTF8"] = "1"
                env["LANG"] = "C.UTF-8"
                env["LC_ALL"] = "C.UTF-8"

            # 2. 关键修改：调用沙箱二进制，把配置文件路径作为参数
            proc = subprocess.Popen(
                [str(self.binary), config_path],  # 不再用 shell=True 直接执行 command
                cwd=str(self.workplace),  # 沙箱进程自身的工作目录
                stdin=subprocess.PIPE if stdin_input is not None else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )

            try:
                stdout_b, stderr_b = proc.communicate(
                    input=stdin_input.encode("utf-8") if stdin_input is not None else None,
                    timeout=time_out + 5,  # 给沙箱留一点清理时间
                )
            except subprocess.TimeoutExpired:
                # 超时：杀进程树
                if os.name == "nt":
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                        capture_output=True,
                    )
                else:
                    proc.kill()
                proc.wait()
                return commandResult(
                    success=False,
                    stdout="",
                    stderr=f"命令执行超时（超过 {time_out} 秒）",
                    exitcode=-1
                )

            # 3. 解码输出
            stdout = _smart_decode(stdout_b)
            stderr = _smart_decode(stderr_b)
            stdout = _truncate_output(stdout)
            stderr = _truncate_output(stderr)

            return commandResult(
                success=proc.returncode == 0,
                stdout=stdout,
                stderr=stderr,
                exitcode=proc.returncode
            )

        except Exception as e:
            return commandResult(
                success=False,
                stdout="",
                stderr=f"命令执行失败：{compress_error(str(e))}。请检查参数或跳过此步骤，建议如实告知用户",
                exitcode=-1
            )
        finally:
            Path(config_path).unlink(missing_ok=True)
            # 清理沙箱工作目录中的临时文件






    def run_code(self, code: str, filename: str,stdin_input: str | None = None, time_out: int = settings.COMMAND_TIMEOUT) -> commandResult:
        script_path = self.workplace / ".MiniCode" / self.session_id / filename   #指定路径为工作目录下的 .MiniCode/session_id/filename
        script_path.write_text(code, encoding="utf-8")
        ext = script_path.suffix.lower()
        template = INTERPRETERS.get(ext)
        if not template:
            return commandResult(
                success=False,
                stdout="",
                stderr=f"不支持的文件类型: {ext}",
                exitcode=-1
            )

        relative_file = script_path.relative_to(self.workplace)
        cmd = f'cmd.exe /c cd /d "{self.workplace}" && {template.format(file=str(relative_file))}'
        return self.run(cmd, stdin_input=stdin_input, time_out=time_out)





    def _build_config(self, command: str, time_out: int) -> dict:
        # 为沙箱进程构建一个配置字典，最终会被写成 JSON 提供给沙箱二进制
        return {
            "version": settings.MXC_version,  # 配置版本
            "containment": settings.MXC_containment,  # 容器/隔离方式（这里使用 processcontainer）
            "process": {
                "commandLine": command  # 要在沙箱中执行的命令行字符串
            },
            "filesystem": {
                "readonlyPaths": [str(self.workplace)],  # 将工作目录作为只读路径（按原逻辑同时也加入可写，会覆盖）
                "readwritePaths": [str(self.workplace)],  # 将工作目录作为可读写路径，允许沙箱进程读写该目录
            },
            "network": {
                "egress": {"default": settings.MXC_network_egress},  # 禁止默认的外发网络访问
                "ingress": {"default": settings.MXC_network_ingress, "hostLoopback": settings.MXC_network_hostLoopback},
                # 禁止入站和回环访问
            }
        }



def _smart_decode(b: bytes) -> str:
    """按字节智能解码：优先UTF-8（程序输出），失败回退GBK（cmd自身错误消息），双双失败才replace"""
    if not b:
        return ""
    for enc in ("utf-8", "gbk"):
        try:
            return b.decode(enc)
        except UnicodeDecodeError:
            continue
    return b.decode("utf-8", errors="replace")



def _truncate_output(text:str) -> str:
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
