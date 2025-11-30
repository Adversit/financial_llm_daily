"""
重试与退信处理模块测试
"""

import pytest
from unittest.mock import MagicMock, patch

from src.mailer.retry_handler import (
    is_hard_bounce,
    send_with_retry,
)


class TestIsHardBounce:
    """测试硬退信检测"""

    def test_hard_bounce_user_not_found(self):
        """测试用户不存在"""
        errors = [
            "User not found",
            "No such user",
            "User unknown",
            "Recipient not found",
        ]

        for error in errors:
            assert is_hard_bounce(error), f"应该识别为硬退信: {error}"

    def test_hard_bounce_mailbox_issues(self):
        """测试邮箱问题"""
        errors = [
            "Mailbox unavailable",
            "Mailbox disabled",
            "Mailbox does not exist",
            "Invalid mailbox",
        ]

        for error in errors:
            assert is_hard_bounce(error), f"应该识别为硬退信: {error}"

    def test_hard_bounce_domain_issues(self):
        """测试域名问题"""
        errors = [
            "Domain not found",
            "Domain does not exist",
        ]

        for error in errors:
            assert is_hard_bounce(error), f"应该识别为硬退信: {error}"

    def test_hard_bounce_smtp_5xx(self):
        """测试 5xx SMTP 错误码"""
        errors = [
            "550 User unknown",
            "554 Permanent error",
            "500 Syntax error",
        ]

        for error in errors:
            assert is_hard_bounce(error), f"应该识别为硬退信: {error}"

    def test_soft_bounce(self):
        """测试软退信（不应该识别为硬退信）"""
        errors = [
            "Connection timeout",
            "Temporary failure",
            "421 Service not available",  # 4xx 是临时错误
            "Rate limit exceeded",
            "Server busy",
        ]

        for error in errors:
            assert not is_hard_bounce(error), f"不应该识别为硬退信: {error}"

    def test_empty_error(self):
        """测试空错误信息"""
        assert not is_hard_bounce("")
        assert not is_hard_bounce(None)


class TestSendWithRetry:
    """测试重试发送"""

    @pytest.mark.asyncio
    async def test_send_with_retry_success_first_try(self):
        """测试第一次就成功"""
        import asyncio

        mock_client = MagicMock()

        # Mock 异步方法
        async def mock_send_email(*args, **kwargs):
            return {"status": "ok", "message_id": "test123"}

        mock_client.send_email = mock_send_email

        email_data = {
            "to": ["test@example.com"],
            "subject": "Test",
            "html_body": "<p>Test</p>",
        }

        result = await send_with_retry(mock_client, email_data, max_retries=2)

        # 应该成功
        assert result["status"] == "ok"

    @pytest.mark.asyncio
    async def test_send_with_retry_success_after_retry(self):
        """测试重试后成功"""
        mock_client = MagicMock()
        call_count = [0]

        # 第一次失败，第二次成功
        async def mock_send_email(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("Temporary error")
            return {"status": "ok", "message_id": "test123"}

        mock_client.send_email = mock_send_email

        email_data = {
            "to": ["test@example.com"],
            "subject": "Test",
            "html_body": "<p>Test</p>",
        }

        result = await send_with_retry(mock_client, email_data, max_retries=2, base_delay=0.01)

        # 应该成功
        assert result["status"] == "ok"

        # 调用了2次
        assert call_count[0] == 2

    @pytest.mark.asyncio
    async def test_send_with_retry_all_failed(self):
        """测试全部失败"""
        mock_client = MagicMock()
        call_count = [0]

        # 全部失败
        async def mock_send_email(*args, **kwargs):
            call_count[0] += 1
            raise Exception("Permanent error")

        mock_client.send_email = mock_send_email

        email_data = {
            "to": ["test@example.com"],
            "subject": "Test",
            "html_body": "<p>Test</p>",
        }

        result = await send_with_retry(mock_client, email_data, max_retries=2, base_delay=0.01)

        # 应该失败
        assert result["status"] == "failed"
        assert "Permanent error" in result["error"]

        # 调用了 3 次（初始 + 2 次重试）
        assert call_count[0] == 3

    @pytest.mark.asyncio
    async def test_send_with_retry_exponential_backoff(self):
        """测试指数退避"""
        import time

        mock_client = MagicMock()

        async def mock_send_email(*args, **kwargs):
            raise Exception("Error")

        mock_client.send_email = mock_send_email

        email_data = {
            "to": ["test@example.com"],
            "subject": "Test",
            "html_body": "<p>Test</p>",
        }

        start_time = time.time()
        await send_with_retry(mock_client, email_data, max_retries=2, base_delay=0.1)
        elapsed = time.time() - start_time

        # 应该至少等待：0.1 + 0.2 = 0.3 秒
        assert elapsed >= 0.3, f"耗时 {elapsed:.2f}s，应该 >= 0.3s"


class TestAddToBlacklist:
    """测试黑名单管理"""

    @patch("src.mailer.retry_handler.get_db")
    def test_add_to_blacklist_existing_recipient(self, mock_get_db):
        """测试将现有收件人加入黑名单"""
        mock_db = MagicMock()
        mock_get_db.return_value.__next__.return_value = mock_db

        # 模拟查询结果
        mock_recipient = MagicMock()
        mock_recipient.enabled = True
        mock_db.query.return_value.filter.return_value.first.return_value = mock_recipient

        from src.mailer.retry_handler import add_to_blacklist

        add_to_blacklist(mock_db, "test@example.com", "test")

        # 应该设置为 disabled
        assert mock_recipient.enabled == False

        # 应该提交
        mock_db.commit.assert_called_once()

    @patch("src.mailer.retry_handler.get_db")
    def test_add_to_blacklist_nonexistent_recipient(self, mock_get_db):
        """测试加入不存在的收件人（应该跳过）"""
        mock_db = MagicMock()
        mock_get_db.return_value.__next__.return_value = mock_db

        # 模拟查询结果为空
        mock_db.query.return_value.filter.return_value.first.return_value = None

        from src.mailer.retry_handler import add_to_blacklist

        # 不应该报错
        add_to_blacklist(mock_db, "nonexistent@example.com", "test")

        # 不应该提交
        mock_db.commit.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
