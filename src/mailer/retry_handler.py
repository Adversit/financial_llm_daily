"""
重试与退信处理模块

实现：
- 失败重试（指数退避）
- 硬退信检测
- 黑名单管理
"""

import asyncio
import re
from typing import Dict, Optional

from loguru import logger
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.mailer.smtp_client import SMTPClient


async def send_with_retry(
    smtp_client: SMTPClient,
    email_data: Dict,
    max_retries: int = 2,
    base_delay: float = 2.0
) -> Dict:
    """
    发送邮件，失败自动重试

    使用指数退避策略：
    - 第1次重试：等待 2 秒
    - 第2次重试：等待 4 秒
    - 第3次重试：等待 8 秒

    Args:
        smtp_client: SMTP 客户端实例
        email_data: 邮件数据字典，包含:
            - to: List[str]
            - subject: str
            - html_body: str
            - bcc: Optional[List[str]]
            - attachments: Optional[List[tuple]]
        max_retries: 最大重试次数
        base_delay: 基础延迟时间（秒）

    Returns:
        发送结果字典（同 smtp_client.send_email）
    """
    last_error = None
    attempt = 0

    while attempt <= max_retries:
        try:
            # 尝试发送
            result = await smtp_client.send_email(
                to=email_data['to'],
                subject=email_data['subject'],
                html_body=email_data['html_body'],
                bcc=email_data.get('bcc'),
                attachments=email_data.get('attachments')
            )

            # 如果成功，直接返回
            if result['status'] == 'ok':
                if attempt > 0:
                    logger.info(f"✅ 重试成功: 第 {attempt} 次重试后成功发送")
                return result

            # 如果返回失败状态，记录错误
            last_error = result.get('error', 'Unknown error')

        except Exception as e:
            last_error = str(e)
            logger.warning(f"⚠️ 发送失败 (尝试 {attempt + 1}/{max_retries + 1}): {last_error}")

        # 如果还有重试次数，等待后重试
        if attempt < max_retries:
            delay = base_delay * (2 ** attempt)  # 指数退避
            logger.info(f"等待 {delay} 秒后重试...")
            await asyncio.sleep(delay)
            attempt += 1
        else:
            # 已达到最大重试次数
            break

    # 所有重试都失败
    logger.error(f"❌ 发送失败，已重试 {max_retries} 次")

    return {
        "message_id": None,
        "status": "failed",
        "error": last_error,
        "retries": attempt,
        "to_count": len(email_data['to']),
        "bcc_count": len(email_data.get('bcc', [])),
    }


def is_hard_bounce(error_message: str) -> bool:
    """
    检测是否为硬退信（永久性失败）

    硬退信类型：
    - 用户不存在（User unknown, No such user）
    - 域名无效（Domain not found）
    - 邮箱被禁用（Mailbox disabled）
    - 邮箱已满（Mailbox full）

    软退信（可重试）：
    - 临时服务器错误
    - 连接超时
    - 速率限制

    Args:
        error_message: 错误信息字符串

    Returns:
        是否为硬退信
    """
    if not error_message:
        return False

    error_lower = error_message.lower()

    # 硬退信特征关键词
    hard_bounce_patterns = [
        r'user (not found|unknown|does not exist)',
        r'no such (user|recipient|mailbox)',
        r'recipient (rejected|not found)',
        r'mailbox (unavailable|disabled|does not exist)',
        r'invalid (recipient|mailbox|address)',
        r'domain (not found|does not exist)',
        r'undeliverable',
        r'permanent (error|failure)',
        r'5[0-9]{2}',  # 5xx SMTP 错误码（永久性错误）
    ]

    for pattern in hard_bounce_patterns:
        if re.search(pattern, error_lower):
            logger.warning(f"检测到硬退信: {pattern} → {error_message[:100]}")
            return True

    return False


def add_to_blacklist(db: Session, email: str, reason: str = "hard_bounce"):
    """
    将邮箱加入黑名单

    在 report_recipients 表中标记 enabled=false

    Args:
        db: 数据库会话
        email: 邮箱地址
        reason: 加入黑名单的原因
    """
    try:
        from src.models.delivery import ReportRecipient

        # 查找该邮箱
        recipient = (
            db.query(ReportRecipient)
            .filter(ReportRecipient.email == email)
            .first()
        )

        if recipient:
            if recipient.enabled:
                recipient.enabled = False
                db.commit()
                logger.warning(
                    f"🚫 邮箱已加入黑名单: {email} (原因: {reason})"
                )
            else:
                logger.debug(f"邮箱已在黑名单中: {email}")
        else:
            logger.debug(f"邮箱不在收件人表中，无需加入黑名单: {email}")

    except Exception as e:
        logger.error(f"加入黑名单失败 {email}: {e}")
        db.rollback()


def remove_from_blacklist(db: Session, email: str):
    """
    将邮箱从黑名单移除

    Args:
        db: 数据库会话
        email: 邮箱地址
    """
    try:
        from src.models.delivery import ReportRecipient

        recipient = (
            db.query(ReportRecipient)
            .filter(ReportRecipient.email == email)
            .first()
        )

        if recipient and not recipient.enabled:
            recipient.enabled = True
            db.commit()
            logger.info(f"✅ 邮箱已从黑名单移除: {email}")
        else:
            logger.debug(f"邮箱未在黑名单中: {email}")

    except Exception as e:
        logger.error(f"移除黑名单失败 {email}: {e}")
        db.rollback()


def get_blacklist(db: Session) -> list[str]:
    """
    获取黑名单邮箱列表

    Args:
        db: 数据库会话

    Returns:
        被禁用的邮箱列表
    """
    try:
        from src.models.delivery import ReportRecipient

        blacklisted = (
            db.query(ReportRecipient.email)
            .filter(ReportRecipient.enabled == False)
            .all()
        )

        return [email for (email,) in blacklisted]

    except Exception as e:
        logger.error(f"获取黑名单失败: {e}")
        return []


async def handle_send_failure(
    db: Session,
    email_batch: Dict,
    error_message: str
):
    """
    处理发送失败情况

    - 检测硬退信
    - 自动加入黑名单
    - 记录日志

    Args:
        db: 数据库会话
        email_batch: 邮件批次信息（包含 to 和 bcc）
        error_message: 错误信息
    """
    # 检测硬退信
    if is_hard_bounce(error_message):
        # 将所有收件人加入黑名单
        all_recipients = email_batch['to'] + email_batch.get('bcc', [])

        for email in all_recipients:
            add_to_blacklist(db, email, reason=f"hard_bounce: {error_message[:50]}")

        logger.warning(
            f"🚫 检测到硬退信，已将 {len(all_recipients)} 个邮箱加入黑名单"
        )
    else:
        # 软退信，记录日志即可
        logger.warning(f"⚠️ 软退信（可重试）: {error_message[:100]}")
