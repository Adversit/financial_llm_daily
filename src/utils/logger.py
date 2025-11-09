"""
日志系统配置
使用 loguru 提供统一的日志记录
"""
from loguru import logger
import sys
from pathlib import Path
from typing import Optional


def setup_logger(
    log_level: str = "INFO",
    log_dir: str = "logs",
    enable_file_logging: bool = True,
    enable_console_logging: bool = True,
):
    """
    配置日志系统

    Args:
        log_level: 日志级别（DEBUG, INFO, WARNING, ERROR, CRITICAL）
        log_dir: 日志文件存储目录
        enable_file_logging: 是否启用文件日志
        enable_console_logging: 是否启用控制台日志
    """

    # 移除默认的日志处理器
    logger.remove()

    # 控制台日志
    if enable_console_logging:
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                   "<level>{level: <8}</level> | "
                   "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                   "<level>{message}</level>",
            level=log_level,
            colorize=True,
        )

    # 文件日志
    if enable_file_logging:
        # 确保日志目录存在
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)

        # 应用日志（每日滚动）
        logger.add(
            f"{log_dir}/app_{{time:YYYY-MM-DD}}.log",
            rotation="00:00",  # 每天午夜滚动
            retention="180 days",  # 保留180天
            level=log_level,
            encoding="utf-8",
            enqueue=True,  # 异步写入，避免阻塞
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        )

        # 错误日志（每日滚动，单独文件）
        logger.add(
            f"{log_dir}/error_{{time:YYYY-MM-DD}}.log",
            rotation="00:00",
            retention="365 days",  # 错误日志保留1年
            level="ERROR",
            encoding="utf-8",
            enqueue=True,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        )

        # 性能日志（用于记录慢操作）
        logger.add(
            f"{log_dir}/performance_{{time:YYYY-MM-DD}}.log",
            rotation="00:00",
            retention="30 days",
            level="WARNING",
            encoding="utf-8",
            enqueue=True,
            filter=lambda record: "PERF" in record["extra"],
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {extra[duration]}ms | {message}",
        )

    logger.info(f"✅ 日志系统初始化完成 (级别: {log_level}, 目录: {log_dir})")


def log_performance(operation: str, duration_ms: float, threshold_ms: float = 1000):
    """
    记录性能日志

    Args:
        operation: 操作名称
        duration_ms: 耗时（毫秒）
        threshold_ms: 阈值，超过此值才记录
    """
    if duration_ms > threshold_ms:
        logger.bind(duration=f"{duration_ms:.2f}", PERF=True).warning(
            f"慢操作: {operation}"
        )


def log_task_start(task_name: str, **kwargs):
    """记录任务开始"""
    params = ", ".join(f"{k}={v}" for k, v in kwargs.items())
    logger.info(f"🚀 任务开始: {task_name} ({params})")


def log_task_end(task_name: str, success: bool = True, duration_ms: Optional[float] = None, **kwargs):
    """记录任务结束"""
    status = "✅ 成功" if success else "❌ 失败"
    duration_info = f", 耗时 {duration_ms:.2f}ms" if duration_ms else ""
    extra = ", ".join(f"{k}={v}" for k, v in kwargs.items())

    if success:
        logger.success(f"{status}: {task_name}{duration_info} ({extra})")
    else:
        logger.error(f"{status}: {task_name}{duration_info} ({extra})")


def log_task_progress(task_name: str, current: int, total: int, message: str = ""):
    """记录任务进度"""
    percentage = (current / total * 100) if total > 0 else 0
    msg = f"⏳ {task_name}: {current}/{total} ({percentage:.1f}%)"
    if message:
        msg += f" - {message}"
    logger.info(msg)


# 默认设置日志
# 在生产环境可以通过环境变量或配置文件控制
try:
    from src.config.settings import settings
    setup_logger(
        log_level=getattr(settings, "LOG_LEVEL", "INFO"),
        log_dir=getattr(settings, "LOG_DIR", "logs"),
    )
except Exception:
    # 配置未加载时使用默认设置
    setup_logger()
