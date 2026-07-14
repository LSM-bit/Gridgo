"""
日志配置

日志输出：
  - 控制台（彩色，开发友好）
  - 文件 logs/gridgo.log（按天轮转，保留 30 天）
"""

import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

# 日志目录
LOG_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# ─── 格式 ───

CONSOLE_FMT = logging.Formatter(
    fmt="%(asctime)s │ %(levelname)-5s │ %(name)s │ %(message)s",
    datefmt="%H:%M:%S",
)

FILE_FMT = logging.Formatter(
    fmt="%(asctime)s │ %(levelname)-5s │ %(name)s │ %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def setup_logger(name: str, level: int = logging.DEBUG) -> logging.Logger:
    """创建带控制台 + 文件输出的 Logger"""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(level)
    logger.propagate = False

    # 控制台
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(CONSOLE_FMT)
    logger.addHandler(console_handler)

    # 文件（每天轮转，保留 30 天）
    file_handler = TimedRotatingFileHandler(
        filename=LOG_DIR / "gridgo.log",
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(FILE_FMT)
    logger.addHandler(file_handler)

    return logger


# ─── 预置 Logger ───

app_logger = setup_logger("gridgo.app")
access_logger = setup_logger("gridgo.access")
