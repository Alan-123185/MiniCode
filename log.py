import sys
from pathlib import Path
from loguru import logger

BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger.remove()   # 去掉 loguru 默认的 stderr 输出，避免重复

# 控制台输出
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | {message}",
)

# 文件输出：固定写到项目根目录下的 logs 目录，并保留较长时间，避免日志被过早清理
logger.add(
    LOG_DIR / "agent_{time}.log",
    rotation="100 MB",
    retention="30 days",
    encoding="utf-8",
    level="DEBUG",
    enqueue=True,
)