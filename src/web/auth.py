"""
OTP 及登录辅助方法
"""
from __future__ import annotations

import random
from typing import Optional

import redis
from loguru import logger

from src.config.settings import settings
from src.mailer.smtp_client import SMTPClient

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)


def generate_otp() -> str:
    """生成 6 位数字验证码"""
    return f"{random.randint(0, 999999):06d}"


def store_otp(email: str, otp: str) -> None:
    """写入 Redis 并设置 TTL"""
    key = f"otp:{email}"
    redis_client.setex(key, settings.OTP_TTL_SECONDS, otp)
    logger.debug("OTP stored for {} (ttl={}s)", email, settings.OTP_TTL_SECONDS)


def verify_otp(email: str, otp: str) -> bool:
    """验证并消费 OTP"""
    key = f"otp:{email}"
    stored = redis_client.get(key)
    if stored is None:
        return False
    if stored == otp:
        redis_client.delete(key)
        return True
    return False


def check_resend_interval(email: str) -> bool:
    """检查是否满足重发间隔"""
    key = f"otp_resend:{email}"
    if redis_client.exists(key):
        return False
    redis_client.setex(key, settings.OTP_RESEND_INTERVAL, "1")
    return True


def increment_otp_attempts(email: str) -> int:
    """增加验证码验证失败次数"""
    key = f"otp_attempts:{email}"
    count = redis_client.incr(key)
    if count == 1:
        redis_client.expire(key, settings.OTP_TTL_SECONDS)
    return count


def check_otp_attempts(email: str) -> bool:
    """检查是否超过最大尝试次数"""
    key = f"otp_attempts:{email}"
    count = redis_client.get(key)
    if count is None:
        return True
    return int(count) < settings.OTP_MAX_ATTEMPTS


def reset_otp_attempts(email: str) -> None:
    """验证成功后重置尝试次数"""
    key = f"otp_attempts:{email}"
    redis_client.delete(key)


async def send_otp_email(email: str, otp: str) -> bool:
    """发送验证码邮件"""
    client = SMTPClient()
    subject = "【金融情报日报】登录验证码"
    html_body = f"""
    <p>您好，</p>
    <p>您的登录验证码为：<strong style="font-size:20px;">{otp}</strong></p>
    <p>验证码有效期 {settings.OTP_TTL_SECONDS // 60} 分钟，请勿泄露。</p>
    <p>如果非本人操作，请忽略本邮件。</p>
    <hr />
    <p style="font-size:12px;color:#888;">金融情报日报系统 · 自动发送</p>
    """
    try:
        result = await client.send_email(to=[email], subject=subject, html_body=html_body)
        return result.get("status") == "ok"
    except Exception as exc:
        logger.error("Failed to send OTP email to {}: {}", email, exc)
        return False
