import sys
from pathlib import Path
from loguru import logger

Path("logs").mkdir(exist_ok=True)

logger.remove()   # 去掉 loguru 默认的 stderr 输出，避免重复

# 控制台输出
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | {message}",
)

# 文件输出
logger.add(
    "logs/agent_{time}.log",
    rotation="10 MB",
    retention="7 days",
    encoding="utf-8",
    level="DEBUG",
    enqueue=True,
)