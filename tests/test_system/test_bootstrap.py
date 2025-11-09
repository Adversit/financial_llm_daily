"""
启动自检模块测试
"""

import pytest
from unittest.mock import MagicMock, patch


class TestCheckRequiredEnvVars:
    """测试环境变量检查"""

    @patch("src.utils.bootstrap.settings")
    def test_check_required_env_vars_success(self, mock_settings):
        """测试所有环境变量都存在"""
        mock_settings.DATABASE_URL = "postgresql://..."
        mock_settings.REDIS_URL = "redis://..."
        mock_settings.SMTP_USER = "user@example.com"
        mock_settings.SMTP_PASS = "password"
        mock_settings.PROVIDER_DEEPSEEK_API_KEY = "sk-xxx"

        from src.utils.bootstrap import check_required_env_vars

        result = check_required_env_vars()

        assert result == True

    @patch("src.utils.bootstrap.settings")
    def test_check_required_env_vars_missing(self, mock_settings):
        """测试缺少环境变量"""
        mock_settings.DATABASE_URL = ""
        mock_settings.REDIS_URL = "redis://..."
        mock_settings.SMTP_USER = ""
        mock_settings.SMTP_PASS = "password"
        mock_settings.PROVIDER_DEEPSEEK_API_KEY = "sk-xxx"

        from src.utils.bootstrap import check_required_env_vars

        result = check_required_env_vars()

        assert result == False


class TestCheckDatabase:
    """测试数据库检查"""

    @patch("src.db.session.get_db")
    def test_check_database_success(self, mock_get_db):
        """测试数据库连接成功"""
        mock_db = MagicMock()
        mock_get_db.return_value.__next__.return_value = mock_db

        from src.utils.bootstrap import check_database

        result = check_database()

        assert result == True

    @patch("src.db.session.get_db")
    def test_check_database_failure(self, mock_get_db):
        """测试数据库连接失败"""
        mock_get_db.side_effect = Exception("Connection error")

        from src.utils.bootstrap import check_database

        result = check_database()

        assert result == False


class TestCheckRedis:
    """测试 Redis 检查"""

    @patch("redis.from_url")
    def test_check_redis_success(self, mock_redis):
        """测试 Redis 连接成功"""
        mock_client = MagicMock()
        mock_redis.return_value = mock_client
        mock_client.ping.return_value = True

        from src.utils.bootstrap import check_redis

        result = check_redis()

        assert result == True

    @patch("redis.from_url")
    def test_check_redis_failure(self, mock_redis):
        """测试 Redis 连接失败"""
        mock_redis.side_effect = Exception("Connection error")

        from src.utils.bootstrap import check_redis

        result = check_redis()

        assert result == False


class TestBootstrap:
    """测试启动自检"""

    @patch("src.utils.bootstrap.check_directories")
    @patch("src.utils.bootstrap.check_redis")
    @patch("src.utils.bootstrap.check_database_tables")
    @patch("src.utils.bootstrap.check_database")
    @patch("src.utils.bootstrap.check_required_env_vars")
    def test_bootstrap_all_pass(
        self,
        mock_env,
        mock_db,
        mock_tables,
        mock_redis,
        mock_dirs
    ):
        """测试所有检查通过"""
        # 所有检查都返回 True
        mock_env.return_value = True
        mock_db.return_value = True
        mock_tables.return_value = True
        mock_redis.return_value = True
        mock_dirs.return_value = True

        from src.utils.bootstrap import bootstrap

        result = bootstrap(skip_smtp=True, skip_llm=True)

        assert result == True

    @patch("src.utils.bootstrap.check_directories")
    @patch("src.utils.bootstrap.check_redis")
    @patch("src.utils.bootstrap.check_database_tables")
    @patch("src.utils.bootstrap.check_database")
    @patch("src.utils.bootstrap.check_required_env_vars")
    def test_bootstrap_critical_failure(
        self,
        mock_env,
        mock_db,
        mock_tables,
        mock_redis,
        mock_dirs
    ):
        """测试必需项检查失败"""
        # 数据库检查失败（必需项）
        mock_env.return_value = True
        mock_db.return_value = False  # 失败
        mock_tables.return_value = True
        mock_redis.return_value = True
        mock_dirs.return_value = True

        from src.utils.bootstrap import bootstrap

        result = bootstrap(skip_smtp=True, skip_llm=True)

        assert result == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
