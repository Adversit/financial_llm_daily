"""
分批与节流模块测试
"""

import pytest
import asyncio
import time

from src.mailer.batcher import (
    batch_recipients,
    RateLimiter,
    validate_email,
    filter_valid_recipients,
    remove_duplicates,
)


class TestBatchRecipients:
    """测试收件人分批"""

    def test_batch_recipients_single_batch(self):
        """测试单批（数量小于限制）"""
        recipients = ["a@test.com", "b@test.com", "c@test.com"]

        batches = batch_recipients(recipients, batch_size=10)

        # 只有一批
        assert len(batches) == 1

        # 第一个在 To，其余在 BCC
        assert batches[0]["to"] == ["a@test.com"]
        assert batches[0]["bcc"] == ["b@test.com", "c@test.com"]

    def test_batch_recipients_multiple_batches(self):
        """测试多批"""
        recipients = [f"user{i}@test.com" for i in range(10)]

        batches = batch_recipients(recipients, batch_size=3)

        # 应该有 4 批（3+3+3+1）
        assert len(batches) == 4

        # 第一批
        assert batches[0]["to"] == ["user0@test.com"]
        assert batches[0]["bcc"] == ["user1@test.com", "user2@test.com"]

        # 第二批
        assert batches[1]["to"] == ["user3@test.com"]
        assert batches[1]["bcc"] == ["user4@test.com", "user5@test.com"]

        # 最后一批（只有1个）
        assert batches[3]["to"] == ["user9@test.com"]
        assert batches[3]["bcc"] == []

    def test_batch_recipients_empty(self):
        """测试空列表"""
        batches = batch_recipients([], batch_size=10)

        assert batches == []

    def test_batch_recipients_exact_size(self):
        """测试刚好等于批大小"""
        recipients = [f"user{i}@test.com" for i in range(5)]

        batches = batch_recipients(recipients, batch_size=5)

        # 只有一批
        assert len(batches) == 1
        assert batches[0]["to"] == ["user0@test.com"]
        assert len(batches[0]["bcc"]) == 4

    def test_batch_recipients_large_dataset(self):
        """测试大量收件人（100人 → 50+50）"""
        recipients = [f"user{i}@test.com" for i in range(100)]

        batches = batch_recipients(recipients, batch_size=50)

        # 应该有 2 批
        assert len(batches) == 2

        # 每批都有 50 个（包括 To 和 BCC）
        assert len(batches[0]["to"]) + len(batches[0]["bcc"]) == 50
        assert len(batches[1]["to"]) + len(batches[1]["bcc"]) == 50


class TestRateLimiter:
    """测试频率限制器"""

    @pytest.mark.asyncio
    async def test_rate_limiter_basic(self):
        """测试基本频率限制"""
        limiter = RateLimiter(rate_per_sec=2.0)  # 每秒2次 = 0.5秒间隔

        start_time = time.time()

        # 连续调用3次
        await limiter.throttle()
        await limiter.throttle()
        await limiter.throttle()

        elapsed = time.time() - start_time

        # 3次调用应该至少花费 2 * 0.5 = 1 秒
        assert elapsed >= 1.0, f"耗时 {elapsed:.2f}s，应该 >= 1.0s"

    @pytest.mark.asyncio
    async def test_rate_limiter_slow_rate(self):
        """测试慢速率（1封/秒）"""
        limiter = RateLimiter(rate_per_sec=1.0)  # 每秒1次 = 1秒间隔

        start_time = time.time()

        # 连续调用2次
        await limiter.throttle()
        await limiter.throttle()

        elapsed = time.time() - start_time

        # 2次调用应该至少花费 1 秒
        assert elapsed >= 1.0, f"耗时 {elapsed:.2f}s，应该 >= 1.0s"

    @pytest.mark.asyncio
    async def test_rate_limiter_reset(self):
        """测试重置功能"""
        limiter = RateLimiter(rate_per_sec=1.0)

        await limiter.throttle()

        # 重置
        limiter.reset()

        start_time = time.time()
        await limiter.throttle()
        elapsed = time.time() - start_time

        # 重置后不应该等待
        assert elapsed < 0.1


class TestValidateEmail:
    """测试邮箱验证"""

    def test_validate_email_valid(self):
        """测试有效邮箱"""
        valid_emails = [
            "test@example.com",
            "user.name@example.com",
            "user+tag@example.co.uk",
            "123@test.cn",
        ]

        for email in valid_emails:
            assert validate_email(email), f"{email} 应该是有效的"

    def test_validate_email_invalid(self):
        """测试无效邮箱"""
        invalid_emails = [
            "invalid",
            "invalid@",
            "@example.com",
            "test@",
            "test@.com",
            "test@example",
            "test @example.com",  # 包含空格
        ]

        for email in invalid_emails:
            assert not validate_email(email), f"{email} 应该是无效的"


class TestFilterValidRecipients:
    """测试过滤有效收件人"""

    def test_filter_valid_recipients(self):
        """测试过滤功能"""
        recipients = [
            "valid1@test.com",
            "invalid",
            "valid2@test.com",
            "@test.com",
            "valid3@test.com",
        ]

        valid = filter_valid_recipients(recipients)

        assert len(valid) == 3
        assert "valid1@test.com" in valid
        assert "valid2@test.com" in valid
        assert "valid3@test.com" in valid

    def test_filter_all_valid(self):
        """测试全部有效"""
        recipients = ["a@test.com", "b@test.com", "c@test.com"]

        valid = filter_valid_recipients(recipients)

        assert len(valid) == 3

    def test_filter_all_invalid(self):
        """测试全部无效"""
        recipients = ["invalid1", "invalid2", "@test.com"]

        valid = filter_valid_recipients(recipients)

        assert len(valid) == 0


class TestRemoveDuplicates:
    """测试去重"""

    def test_remove_duplicates_basic(self):
        """测试基本去重"""
        recipients = [
            "a@test.com",
            "b@test.com",
            "a@test.com",  # 重复
            "c@test.com",
            "b@test.com",  # 重复
        ]

        unique = remove_duplicates(recipients)

        assert len(unique) == 3
        assert unique == ["a@test.com", "b@test.com", "c@test.com"]

    def test_remove_duplicates_no_duplicates(self):
        """测试无重复"""
        recipients = ["a@test.com", "b@test.com", "c@test.com"]

        unique = remove_duplicates(recipients)

        assert len(unique) == 3
        assert unique == recipients

    def test_remove_duplicates_all_same(self):
        """测试全部相同"""
        recipients = ["a@test.com"] * 5

        unique = remove_duplicates(recipients)

        assert len(unique) == 1
        assert unique == ["a@test.com"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
