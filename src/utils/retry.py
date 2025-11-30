"""
重试机制工具
基于 tenacity 库提供统一的重试策略
"""
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
from loguru import logger
import asyncio


def retry_with_backoff(max_attempts: int = 3, min_wait: int = 1, max_wait: int = 10):
    """
    指数退避重试装饰器

    Args:
        max_attempts: 最大尝试次数
        min_wait: 最小等待秒数
        max_wait: 最大等待秒数

    Returns:
        装饰器函数
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        before_sleep=before_sleep_log(logger, "WARNING"),
        reraise=True
    )


def retry_on_network_error(max_attempts: int = 3):
    """
    网络错误重试装饰器

    Args:
        max_attempts: 最大尝试次数

    Returns:
        装饰器函数
    """
    import requests
    import httpx

    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((
            requests.RequestException,
            httpx.RequestError,
            TimeoutError,
            ConnectionError
        )),
        before_sleep=before_sleep_log(logger, "WARNING"),
        reraise=True
    )


async def async_retry_with_backoff(
    coro,
    max_attempts: int = 3,
    min_wait: int = 1,
    max_wait: int = 10
):
    """
    异步函数的手动重试逻辑

    Args:
        coro: 协程函数
        max_attempts: 最大尝试次数
        min_wait: 最小等待秒数
        max_wait: 最大等待秒数

    Returns:
        协程函数的返回值
    """
    for attempt in range(1, max_attempts + 1):
        try:
            return await coro
        except Exception as e:
            if attempt >= max_attempts:
                logger.error(f"重试失败,已达最大次数 {max_attempts}: {e}")
                raise
            wait_time = min(min_wait * (2 ** (attempt - 1)), max_wait)
            logger.warning(f"尝试 {attempt}/{max_attempts} 失败: {e}, {wait_time}秒后重试...")
            await asyncio.sleep(wait_time)
