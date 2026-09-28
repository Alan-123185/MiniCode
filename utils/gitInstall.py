import os
import shutil
import subprocess
import sys
from pathlib import Path
from loguru import logger
from exceptions import BizException


def _refresh_process_path():
    """读取注册表，强制刷新当前 Python 进程的 PATH 环境变量"""
    try:
        import winreg
        # 读取 System 的 PATH
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r'SYSTEM\CurrentControlSet\Control\Session Manager\Environment') as key:
            sys_path, _ = winreg.QueryValueEx(key, 'Path')
        # 读取 User 的 PATH
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Environment') as key:
            user_path, _ = winreg.QueryValueEx(key, 'Path')

        # 更新当前进程的环境变量
        os.environ['PATH'] = os.path.expandvars(f"{sys_path};{user_path}")
    except Exception as e:
        logger.warning(f"刷新环境变量失败，尝试拼接默认 Git 路径: {e}")
        # 保底方案：手动硬编码常见的 Git 安装路径
        default_paths = [
            r"C:\Program Files\Git\cmd",
            r"C:\Program Files (x86)\Git\cmd",
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Git\cmd")
        ]
        os.environ['PATH'] += ";" + ";".join(default_paths)


def install_git_by_winget() -> bool:
    # 1. 先检查系统是否存在 winget
    if not shutil.which("winget"):
        logger.error("系统缺少 winget 工具，无法通过此方式安装")
        return False

    try:
        # 2. 执行静默安装
        result = subprocess.run(
            [
                "winget", "install",
                "--id", "Git.Git",
                "-e",
                "--source", "winget",
                "--silent",
                "--accept-source-agreements",
                "--accept-package-agreements"
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        if result.returncode != 0:
            logger.error(f"winget 安装失败，返回码: {result.returncode}")
            return False

        # 3. 关键修正：重新加载环境变量，让当前进程认识 git
        _refresh_process_path()

        # 4. 再次校验 git 是否已就绪
        git_executable = shutil.which("git") or "git"
        verify_result = subprocess.run(
            [git_executable, "--version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return verify_result.returncode == 0

    except Exception as e:
        logger.error(f"安装 Git 时发生异常: {e}")
        return False


def is_git_installed() -> bool:
    """检查系统是否已安装 Git"""
    try:
        git_executable = shutil.which("git") or "git"
        result = subprocess.run(
            [git_executable, "--version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return result.returncode == 0
    except Exception as e:
        logger.error(f"检查 Git 安装状态时发生异常: {e}")
        return False


def check_git() -> bool:
    if is_git_installed():
        with open(get_exe_dir() / ".env", "a+", encoding="utf-8") as f:
            f.seek(0)
            content = f.read()
            if "GIT_BASH_PATH" in content:
                return True
            else:
                bash_path = find_git_path()
                create_env(bash_path)
                return True
    else:
        logger.warning("Git 未安装，尝试安装...")
        if install_git_by_winget():
            logger.info("Git 安装成功")
        else:
            logger.error("Git 安装失败，请手动安装 Git 并确保其在 PATH 中")
            raise BizException(message="Git 安装失败，请手动安装 Git 并确保其在 PATH 中")
        bash_path = find_git_path()
        create_env(bash_path)
        return True






def find_git_path() -> str :
    """查找 Git Bash 的 bash.exe（优先 PATH，其次常见安装目录）"""

    def _find_bash_from_git() -> str | None:
        git_exe = shutil.which("git")
        if not git_exe:
            return None
        root = Path(git_exe).parent.parent  # 从 cmd\ 或 bin\ 上跳两级到 Git 根目录
        for sub in ("bin", "usr/bin"):
            candidate = root / sub / "bash.exe"
            if candidate.is_file():
                return str(candidate)
        which_bash = shutil.which("bash")
        if which_bash and "System32" not in which_bash:
            return which_bash
        return None

    git_path= _find_bash_from_git()
    if git_path:
        return git_path
    # 2. 常见安装路径
    candidates = [
        # 标准安装（管理员）
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files (x86)\Git\bin\bash.exe",
        # 用户级安装（非管理员 / winget 默认）
        os.path.expanduser(r"~\AppData\Local\Programs\Git\bin\bash.exe"),
        # 备选：MSYS2 的 bash
        r"C:\Program Files\Git\usr\bin\bash.exe",
        r"C:\Program Files (x86)\Git\usr\bin\bash.exe",
    ]
    for p in candidates:
        if p and os.path.isfile(p):
            return p
    raise BizException(message="未找到可用的 Git Bash , 请手动配置.env")




def create_env(git_path: str) -> bool:
    path=get_exe_dir() / ".env"
    if not path.exists():
        path.write_text("GIT_BASH_PATH=" + git_path, encoding="utf-8")
        return True
    return False



#打包之后的根目录
def get_exe_dir() -> Path:
    if getattr(sys, "frozen", False):
        # 打包后：exe 所在目录
        return Path(sys.executable).parent
    # 开发时：项目目录（按你代码结构调）
    return Path(__file__).resolve().parent.parent