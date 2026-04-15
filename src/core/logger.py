"""
日志模块
使用 loguru 提供现代化日志功能
"""

import sys
from pathlib import Path
from loguru import logger

from .exceptions import ConfigLoadError


def setup_logger(
    level: str = "INFO",
    log_dir: str = "logs",
    rotation: str = "00:00",
    retention: str = "7 days",
    save_to_file: bool = True
) -> None:
    """
    配置日志系统

    Args:
        level: 日志级别
        log_dir: 日志目录
        rotation: 日志轮转时间
        retention: 日志保留时间
        save_to_file: 是否保存到文件
    """
    # 移除默认 handler
    logger.remove()

    # 添加控制台输出
    logger.add(
        sys.stderr,
        level=level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True
    )

    # 添加文件输出
    if save_to_file:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)

        logger.add(
            log_path / "run_{time}.log",
            level=level,
            rotation=rotation,
            retention=retention,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            encoding="utf-8",
            enqueue=True  # 线程安全
        )


def get_logger():
    """获取 logger 实例"""
    return logger
