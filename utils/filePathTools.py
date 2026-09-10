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