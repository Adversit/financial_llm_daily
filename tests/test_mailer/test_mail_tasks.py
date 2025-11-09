"""
邮件任务模块测试
"""

import pytest
from datetime import date, datetime, time
from unittest.mock import AsyncMock, MagicMock, patch

from src.tasks.mail_tasks import (
    _send_report_core_logic,
    check_time_window,
)


class TestCheckTimeWindow:
    """测试时间窗口检查"""

    def test_check_time_window_within(self):
        """测试在窗口内"""
        # 当前时间 06:10，窗口 06:00-07:00
        current = datetime(2025, 11, 6, 6, 10, 0)

        result = check_time_window(
            start="06:00",
            end="07:00",
            current_time=current
        )

        assert result == True

    def test_check_time_window_before(self):
        """测试在窗口之前"""
        # 当前时间 05:50，窗口 06:00-07:00
        current = datetime(2025, 11, 6, 5, 50, 0)

        result = check_time_window(
            start="06:00",
            end="07:00",
            current_time=current
        )

        assert result == False

    def test_check_time_window_after(self):
        """测试在窗口之后"""
        # 当前时间 07:10，窗口 06:00-07:00
        current = datetime(2025, 11, 6, 7, 10, 0)

        result = check_time_window(
            start="06:00",
            end="07:00",
            current_time=current
        )

        assert result == False

    def test_check_time_window_at_start(self):
        """测试在起始边界"""
        # 当前时间 06:00，窗口 06:00-07:00
        current = datetime(2025, 11, 6, 6, 0, 0)

        result = check_time_window(
            start="06:00",
            end="07:00",
            current_time=current
        )

        assert result == True

    def test_check_time_window_at_end(self):
        """测试在结束边界"""
        # 当前时间 07:00，窗口 06:00-07:00
        current = datetime(2025, 11, 6, 7, 0, 0)

        result = check_time_window(
            start="06:00",
            end="07:00",
            current_time=current
        )

        assert result == True

    def test_check_time_window_overnight(self):
        """测试跨午夜的窗口"""
        # 窗口 23:00-01:00

        # 23:30 应该在窗口内
        current1 = datetime(2025, 11, 6, 23, 30, 0)
        assert check_time_window("23:00", "01:00", current1) == True

        # 00:30 应该在窗口内
        current2 = datetime(2025, 11, 6, 0, 30, 0)
        assert check_time_window("23:00", "01:00", current2) == True

        # 02:00 应该在窗口外
        current3 = datetime(2025, 11, 6, 2, 0, 0)
        assert check_time_window("23:00", "01:00", current3) == False


class TestSendReportCoreLogic:
    """测试邮件发送核心逻辑"""

    @patch("src.tasks.mail_tasks.check_time_window")
    @patch("src.tasks.mail_tasks.get_db")
    @patch("src.tasks.mail_tasks._send_batches_async", new_callable=AsyncMock)
    def test_send_report_success(
        self,
        mock_send_batches_async,
        mock_get_db,
        mock_check_window
    ):
        """测试成功发送"""
        # Mock 数据库
        mock_db = MagicMock()
        mock_get_db.return_value.__next__.return_value = mock_db

        # Mock 时间窗口检查
        mock_check_window.return_value = True

        # Mock 报告查询
        mock_report = MagicMock()
        mock_report.id = 1
        mock_report.html_body = "<html>正文</html>"
        mock_report.html_attachment = "<html>附件</html>"

        # Mock 收件人查询
        mock_recipients = [("test1@example.com",), ("test2@example.com",)]

        # 需要分别 mock 两次不同的查询
        mock_query_obj = MagicMock()
        mock_filter_obj = MagicMock()

        # 第一次查询（报告）
        mock_filter_obj.first.return_value = mock_report

        # 第二次查询（收件人）
        mock_filter_obj.all.return_value = mock_recipients

        mock_query_obj.filter.return_value = mock_filter_obj
        mock_db.query.return_value = mock_query_obj

        # Mock 异步发送结果
        mock_send_batches_async.return_value = [
            {"status": "ok", "message_id": "msg1"},
        ]

        # 调用
        result = _send_report_core_logic("2025-11-06")

        # 验证
        assert result["status"] == "success"
        assert result["report_id"] == 1
        assert result["success_batches"] == 1

    @patch("src.tasks.mail_tasks.check_time_window")
    @patch("src.tasks.mail_tasks.get_db")
    def test_send_report_not_in_time_window(
        self,
        mock_get_db,
        mock_check_window
    ):
        """测试不在时间窗口内"""
        mock_db = MagicMock()
        mock_get_db.return_value.__next__.return_value = mock_db

        # Mock 时间窗口检查为 False
        mock_check_window.return_value = False

        result = _send_report_core_logic("2025-11-06")

        # 应该跳过
        assert result["status"] == "skipped"
        assert result["reason"] == "not_in_time_window"

    @patch("src.tasks.mail_tasks.check_time_window")
    @patch("src.tasks.mail_tasks.get_db")
    def test_send_report_report_not_found(
        self,
        mock_get_db,
        mock_check_window
    ):
        """测试报告不存在"""
        mock_db = MagicMock()
        mock_get_db.return_value.__next__.return_value = mock_db

        # Mock 时间窗口检查
        mock_check_window.return_value = True

        # Mock 报告不存在
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = _send_report_core_logic("2025-11-06")

        # 应该报错
        assert result["status"] == "error"
        assert result["error"] == "report_not_found"

    @patch("src.tasks.mail_tasks.check_time_window")
    @patch("src.tasks.mail_tasks.get_db")
    def test_send_report_no_recipients(
        self,
        mock_get_db,
        mock_check_window
    ):
        """测试没有收件人"""
        mock_db = MagicMock()
        mock_get_db.return_value.__next__.return_value = mock_db

        # Mock 时间窗口检查
        mock_check_window.return_value = True

        # Mock 报告
        mock_report = MagicMock()
        mock_report.id = 1
        mock_db.query.return_value.filter.return_value.first.return_value = mock_report

        # Mock 没有收件人
        mock_recipients_query = MagicMock()
        mock_recipients_query.all.return_value = []
        mock_db.query.return_value.filter.return_value = mock_recipients_query

        result = _send_report_core_logic("2025-11-06")

        # 应该跳过
        assert result["status"] == "skipped"
        assert result["reason"] == "no_recipients"


class TestCeleryTaskExecution:
    """测试 Celery 任务执行"""

    def test_task_is_registered(self):
        """测试任务已注册"""
        from src.tasks.celery_app import celery_app
        from src.tasks.mail_tasks import send_report_task

        # 验证任务已注册
        assert send_report_task.name in celery_app.tasks

    def test_task_has_correct_route(self):
        """测试任务路由正确"""
        from src.tasks.celery_app import celery_app

        # 验证任务路由配置
        task_routes = celery_app.conf.task_routes
        assert "src.tasks.mail_tasks.*" in task_routes
        assert task_routes["src.tasks.mail_tasks.*"]["queue"] == "mail"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
