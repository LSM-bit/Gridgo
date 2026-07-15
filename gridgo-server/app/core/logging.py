"""
日志配置

日志输出：控制台（彩色，开发友好）
"""

import logging
import sys

# ─── 格式 ───

CONSOLE_FMT = logging.Formatter(
    fmt="%(asctime)s │ %(levelname)-5s │ %(name)s │ %(message)s",
    datefmt="%H:%M:%S",
)


def setup_logger(name: str, level: int = logging.DEBUG) -> logging.Logger:
    """创建带控制台输出的 Logger"""
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

    return logger


# ─── 预置 Logger ───

app_logger = setup_logger("gridgo.app")
access_logger = setup_logger("gridgo.access")
