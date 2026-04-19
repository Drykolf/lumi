from pathlib import Path
from loguru import logger

_LOG_PATH = Path(__file__).parent / "lumi.log"

logger.add(
    str(_LOG_PATH),
    filter=lambda r: r["name"].startswith("custom."),
    level="DEBUG",
    rotation="5 MB",
    retention=5,
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
    encoding="utf-8",
)
