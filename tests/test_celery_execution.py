"""
测试 Celery 任务实际执行（临时测试文件）
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import date


def test_celery_task_execution_in_eager_mode():
    """测试 Celery 任务在 eager 模式下的执行"""
    from src.tasks.celery_app import celery_app
    from src.tasks.report_tasks import build_report_task

    # 设置为 eager 模式（同步执行，便于测试）
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True

    # Mock 所有依赖
    with patch("src.tasks.report_tasks.get_db") as mock_get_db, \
         patch("src.tasks.report_tasks.filter_items") as mock_filter_items, \
         patch("src.tasks.report_tasks.section_and_sort") as mock_section, \
         patch("src.tasks.report_tasks.select_topn") as mock_topn, \
         patch("src.tasks.report_tasks.generate_overview") as mock_overview, \
         patch("src.tasks.report_tasks.build_email_body") as mock_body, \
         patch("src.tasks.report_tasks.build_attachment") as mock_attach, \
         patch("src.tasks.report_tasks.build_metadata") as mock_meta, \
         patch("src.tasks.report_tasks.get_sections_statistics") as mock_stats:

        # 设置 mock
        mock_db = MagicMock()
        mock_get_db.return_value.__next__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = None

        mock_filter_items.return_value = [{"id": 1}]
        mock_section.return_value = {"国内": {"政治": [{"id": 1}]}}
        mock_topn.return_value = {"国内": {"政治": [{"id": 1}]}}
        mock_overview.return_value = "测试摘要"
        mock_body.return_value = "<html>正文</html>"
        mock_attach.return_value = "<html>附件</html>"
        mock_meta.return_value = {"total_items": 1, "build_time_ms": 100}
        mock_stats.return_value = {"total_items": 1}

        # 使用 apply() 同步执行任务
        result = build_report_task.apply(args=["2025-11-05"])
        result_data = result.get()

        # 验证结果
        assert result_data["status"] == "success"
        assert "report_id" in result_data
        assert result_data["report_date"] == "2025-11-05"

        print("✅ Celery 任务执行成功！")
        print(f"   结果: {result_data}")


def test_celery_task_with_default_date():
    """测试不传日期参数（使用默认值）"""
    from src.tasks.celery_app import celery_app
    from src.tasks.report_tasks import build_report_task

    celery_app.conf.task_always_eager = True

    with patch("src.tasks.report_tasks.get_db") as mock_get_db, \
         patch("src.tasks.report_tasks.filter_items") as mock_filter_items, \
         patch("src.tasks.report_tasks.build_email_body") as mock_body, \
         patch("src.tasks.report_tasks.build_attachment") as mock_attach, \
         patch("src.tasks.report_tasks.build_metadata") as mock_meta, \
         patch("src.tasks.report_tasks.get_sections_statistics") as mock_stats:

        mock_db = MagicMock()
        mock_get_db.return_value.__next__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = None

        mock_filter_items.return_value = []
        mock_body.return_value = "<html>空报告</html>"
        mock_attach.return_value = "<html>空附件</html>"
        mock_meta.return_value = {"total_items": 0, "build_time_ms": 50}
        mock_stats.return_value = {"total_items": 0}

        # 不传参数，使用默认日期
        result = build_report_task.apply()
        result_data = result.get()

        # 验证结果
        assert result_data["status"] == "success"
        assert result_data["report_date"] == date.today().isoformat()

        print("✅ 使用默认日期的任务执行成功！")


if __name__ == "__main__":
    test_celery_task_execution_in_eager_mode()
    test_celery_task_with_default_date()
    print("\n🎉 所有 Celery 任务执行测试通过！")
