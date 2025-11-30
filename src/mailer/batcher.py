"""
分批与节流模块

实现收件人分批和发送频率控制。
"""

import asyncio
import time
from typing import List, Dict

from loguru import logger

from src.config.settings import settings


def batch_recipients(
    recipients: List[str],
    batch_size: int = None
) -> List[Dict[str, List[str]]]:
    """
    将收件人列表分批

    策略：
    - 第一个邮箱放在 To 字段（作为主收件人）
    - 其余邮箱放在 BCC 字段（密送，保护隐私）
    - 每批最多 batch_size 个收件人

    Args:
        recipients: 收件人邮箱列表
        batch_size: 每批最大收件人数，默认从配置读取

    Returns:
        分批结果列表，格式:
        [
            {"to": [email1], "bcc": [email2, ..., emailN]},
            {"to": [emailN+1], "bcc": [emailN+2, ..., email2N]},
            ...
        ]

    Examples:
        >>> batch_recipients(['a@x.com', 'b@x.com', 'c@x.com'], batch_size=2)
        [
            {"to": ["a@x.com"], "bcc": ["b@x.com"]},
            {"to": ["c@x.com"], "bcc": []}
        ]
    """
    batch_size = batch_size or settings.MAIL_BATCH_LIMIT

    if not recipients:
        return []

    if len(recipients) <= batch_size:
        # 只有一批
        return [{
            "to": [recipients[0]],
            "bcc": recipients[1:] if len(recipients) > 1 else []
        }]

    # 分批
    batches = []
    for i in range(0, len(recipients), batch_size):
        batch = recipients[i:i + batch_size]
        batches.append({
            "to": [batch[0]],
            "bcc": batch[1:] if len(batch) > 1 else []
        })

    logger.info(
        f"收件人分批: {len(recipients)} 个 → {len(batches)} 批 "
        f"(每批最多 {batch_size} 个)"
    )

    return batches


class RateLimiter:
    """
    发送频率限制器

    实现：
    - 控制每秒最多发送 N 封邮件
    - 使用令牌桶算法
    - 支持异步调用
    """

    def __init__(self, rate_per_sec: float = None):
        """
        初始化频率限制器

        Args:
            rate_per_sec: 每秒允许发送的邮件数（例如 1.0 表示每秒1封）
        """
        self.rate = rate_per_sec or settings.MAIL_RATE_LIMIT_PER_SEC
        self.interval = 1.0 / self.rate  # 每封邮件的间隔时间（秒）
        self.last_call = 0.0

        logger.info(f"初始化频率限制器: {self.rate} 封/秒（间隔 {self.interval:.2f} 秒）")

    async def throttle(self):
        """
        等待直到允许发送下一封邮件

        实现：
        - 计算距离上次发送的时间
        - 如果间隔不足，则等待
        - 记录当前时间作为新的发送时间
        """
        current_time = time.time()
        elapsed = current_time - self.last_call

        if elapsed < self.interval:
            wait_time = self.interval - elapsed
            logger.debug(f"频率限制: 等待 {wait_time:.2f} 秒...")
            await asyncio.sleep(wait_time)

        self.last_call = time.time()

    def reset(self):
        """重置限制器（用于测试）"""
        self.last_call = 0.0


def validate_email(email: str) -> bool:
    """
    验证邮箱格式是否合法

    Args:
        email: 邮箱地址

    Returns:
        是否合法
    """
    import re

    # 简单的邮箱正则
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def filter_valid_recipients(recipients: List[str]) -> List[str]:
    """
    过滤有效的收件人邮箱

    Args:
        recipients: 收件人列表

    Returns:
        有效的收件人列表
    """
    valid = []
    invalid = []

    for email in recipients:
        if validate_email(email):
            valid.append(email)
        else:
            invalid.append(email)

    if invalid:
        logger.warning(f"发现 {len(invalid)} 个无效邮箱: {invalid}")

    return valid


def remove_duplicates(recipients: List[str]) -> List[str]:
    """
    去重收件人列表（保持顺序）

    Args:
        recipients: 收件人列表

    Returns:
        去重后的收件人列表
    """
    seen = set()
    result = []

    for email in recipients:
        if email not in seen:
            seen.add(email)
            result.append(email)

    if len(result) < len(recipients):
        logger.info(f"收件人去重: {len(recipients)} → {len(result)}")

    return result
