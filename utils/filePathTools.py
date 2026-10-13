import os
import sys
from pathlib import Path
from langchain_core.runnables import RunnableConfig
from config.dependencies import get_session


def relativePathToAbsolute(file_path: str,config:RunnableConfig) -> Path:
    """将相对路径转换为基于项目根目录的绝对路径"""
    session =get_session(config)
    return Path(session.workplace) / file_path


def absolutePathToRelative(file_path: str,config:RunnableConfig) -> Path:
    session =get_session(config)
    """将绝对路径转化为基于项目根目录的相对路径"""
    abs_path = Path(file_path).resolve()          # 1. 规范化绝对路径
    root_path = Path(session.workplace).resolve()  # 2. 规范化根目录
    try:
        # 3. 计算相对路径（核心）
        return abs_path.relative_to(root_path)
    except ValueError:
        # 如果传入的路径不在项目根目录下，可以返回原路径，或者抛出更友好的异常
        # 这里选择返回原绝对路径（或你可以选择抛出异常）
        return abs_path



def is_path_safe(abs_path: Path,workplace: Path) -> bool:
    """检查路径是否安全，即是否在项目根目录下"""
    try:
        abs_path.relative_to(workplace)
        return True
    except ValueError:
        return False




def app_root() -> Path:
    """
    返回应用根目录。
    - 打包后（PyInstaller）：exe 所在目录
    - 开发环境：项目根目录（main.py 所在目录）
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后，sys.executable 是 exe 的完整路径
        return Path(sys.executable).resolve().parent
    else:
        # 开发环境，以项目根目录为准
        # 如果 paths.py 在 utils/ 下，parent.parent 就是项目根
        return Path(__file__).resolve().parent.parent


def resource_path(relative: str) -> Path:
    """基于 app_root 拼资源路径"""
    return app_root() / relative



def data_dir() -> Path:
    """可写数据目录（数据库、日志）"""
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home())) / "MiniCode"
    else:
        base = Path.home() / ".local" / "share" / "MiniCode"
    base.mkdir(parents=True, exist_ok=True)
    return base