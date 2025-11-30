"""
日志系统测试
"""

import pytest
from pathlib import Path
from loguru import logger


class TestSetupLogger:
    """测试日志系统配置"""

    def test_setup_logger_default(self, tmp_path):
        """测试默认配置"""
        from src.utils.logger import setup_logger

        # 使用临时目录
        log_dir = str(tmp_path / "logs")

        setup_logger(log_dir=log_dir)

        # 验证日志目录被创建
        assert Path(log_dir).exists()

    def test_setup_logger_custom_level(self, tmp_path):
        """测试自定义日志级别"""
        from src.utils.logger import setup_logger

        log_dir = str(tmp_path / "logs")

        setup_logger(log_level="DEBUG", log_dir=log_dir)

        # 日志系统应该正常配置
        assert Path(log_dir).exists()


class TestLogPerformance:
    """测试性能日志"""

    def test_log_performance_above_threshold(self):
        """测试超过阈值的性能日志"""
        from src.utils.logger import log_performance

        # 不应该抛出异常
        log_performance("test_operation", duration_ms=2000, threshold_ms=1000)

    def test_log_performance_below_threshold(self):
        """测试低于阈值的性能日志"""
        from src.utils.logger import log_performance

        # 不应该抛出异常
        log_performance("test_operation", duration_ms=500, threshold_ms=1000)


class TestLogTaskHelpers:
    """测试任务日志辅助函数"""

    def test_log_task_start(self):
        """测试任务开始日志"""
        from src.utils.logger import log_task_start

        # 不应该抛出异常
        log_task_start("test_task", param1="value1", param2="value2")

    def test_log_task_end_success(self):
        """测试任务成功结束日志"""
        from src.utils.logger import log_task_end

        # 不应该抛出异常
        log_task_end("test_task", success=True, duration_ms=1000, items=10)

    def test_log_task_end_failure(self):
        """测试任务失败结束日志"""
        from src.utils.logger import log_task_end

        # 不应该抛出异常
        log_task_end("test_task", success=False, duration_ms=500, error="Test error")

    def test_log_task_progress(self):
        """测试任务进度日志"""
        from src.utils.logger import log_task_progress

        # 不应该抛出异常
        log_task_progress("test_task", current=5, total=10, message="Processing...")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
