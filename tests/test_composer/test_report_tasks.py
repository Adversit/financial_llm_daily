"""
报告任务模块测试
"""

import json
import pytest
from datetime import date, datetime, timedelta
from unittest.mock import patch, MagicMock, call

# 直接导入核心逻辑函数（不是Celery任务包装的版本）
from src.tasks.report_tasks import (
    _build_report_core_logic,
    _build_report_batch_core_logic,
)


class TestBuildReportTaskLogic:
    """测试报告构建任务的核心逻辑"""

    @patch("src.tasks.report_tasks.get_db")
    @patch("src.tasks.report_tasks.filter_items")
    @patch("src.tasks.report_tasks.section_and_sort")
    @patch("src.tasks.report_tasks.select_topn")
    @patch("src.tasks.report_tasks.generate_overview")
    @patch("src.tasks.report_tasks.build_email_body")
    @patch("src.tasks.report_tasks.build_attachment")
    @patch("src.tasks.report_tasks.build_metadata")
    @patch("src.tasks.report_tasks.get_sections_statistics")
    def test_build_report_with_items(
        self,
        mock_get_stats,
        mock_build_metadata,
        mock_build_attachment,
        mock_build_email_body,
        mock_generate_overview,
        mock_select_topn,
        mock_section_and_sort,
        mock_filter_items,
        mock_get_db,
    ):
        """测试有抽取项时的报告构建"""
        # 设置 mock 数据库
        mock_db = MagicMock()
        mock_get_db.return_value.__next__.return_value = mock_db

        # 设置 mock 返回值
        mock_filter_items.return_value = [
            {"id": 1, "fact": "测试事实1"},
            {"id": 2, "fact": "测试事实2"},
        ]

        mock_sections = {
            "国内": {
                "政治": [{"id": 1}],
            }
        }
        mock_section_and_sort.return_value = mock_sections

        mock_topn_sections = {
            "国内": {
                "政治": [{"id": 1}],
            }
        }
        mock_select_topn.return_value = mock_topn_sections

        mock_generate_overview.return_value = "测试摘要"
        mock_build_email_body.return_value = "<html>正文</html>"
        mock_build_attachment.return_value = "<html>附件</html>"

        mock_metadata = {
            "total_items": 2,
            "topn_items": 1,
            "build_time_ms": 100,
        }
        mock_build_metadata.return_value = mock_metadata

        mock_get_stats.return_value = {
            "total_items": 2,
            "regions": {},
        }

        # 模拟不存在已有报告
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # 直接调用核心逻辑函数（无需处理Celery装饰器）
        result = _build_report_core_logic("2025-11-05")

        # 验证结果
        assert result["status"] == "success"
        assert "report_id" in result
        assert result["report_date"] == "2025-11-05"
        assert result["metadata"]["total_items"] == 2

        # 验证各个函数被调用
        mock_filter_items.assert_called_once()
        mock_section_and_sort.assert_called_once()
        mock_select_topn.assert_called_once()
        mock_generate_overview.assert_called_once()
        mock_build_email_body.assert_called_once()
        mock_build_attachment.assert_called_once()
        mock_build_metadata.assert_called_once()

        # 验证数据库操作
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @patch("src.tasks.report_tasks.get_db")
    @patch("src.tasks.report_tasks.filter_items")
    @patch("src.tasks.report_tasks.build_email_body")
    @patch("src.tasks.report_tasks.build_attachment")
    @patch("src.tasks.report_tasks.build_metadata")
    @patch("src.tasks.report_tasks.get_sections_statistics")
    def test_build_report_empty_items(
        self,
        mock_get_stats,
        mock_build_metadata,
        mock_build_attachment,
        mock_build_email_body,
        mock_filter_items,
        mock_get_db,
    ):
        """测试没有抽取项的情况"""
        # 设置 mock 数据库
        mock_db = MagicMock()
        mock_get_db.return_value.__next__.return_value = mock_db

        # 设置空的抽取项
        mock_filter_items.return_value = []

        mock_build_email_body.return_value = "<html>空报告</html>"
        mock_build_attachment.return_value = "<html>空附件</html>"

        mock_metadata = {
            "total_items": 0,
            "topn_items": 0,
            "build_time_ms": 50,
        }
        mock_build_metadata.return_value = mock_metadata

        mock_get_stats.return_value = {
            "total_items": 0,
            "regions": {},
        }

        # 模拟不存在已有报告
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # 直接调用核心逻辑函数
        result = _build_report_core_logic("2025-11-05")

        # 验证结果
        assert result["status"] == "success"
        assert result["metadata"]["total_items"] == 0

        # 验证空报告仍然生成
        mock_build_email_body.assert_called_once()
        mock_build_attachment.assert_called_once()

    @patch("src.tasks.report_tasks.get_db")
    @patch("src.tasks.report_tasks.filter_items")
    def test_build_report_error_handling(
        self,
        mock_filter_items,
        mock_get_db,
    ):
        """测试错误处理"""
        # 设置 mock 数据库
        mock_db = MagicMock()
        mock_get_db.return_value.__next__.return_value = mock_db

        # 模拟异常
        mock_filter_items.side_effect = Exception("测试异常")

        # 直接调用核心逻辑函数
        result = _build_report_core_logic("2025-11-05")

        # 验证错误结果
        assert result["status"] == "error"
        assert "测试异常" in result["error"]
        assert result["report_date"] == "2025-11-05"

        # 验证回滚
        mock_db.rollback.assert_called_once()


class TestScorerIntegration:
    """测试评分器集成功能（不需要数据库）"""

    def test_scorer_functions_work_together(self):
        """测试评分器各函数协同工作"""
        from src.composer.scorer import (
            calculate_score,
            section_and_sort,
            select_topn,
        )

        # 创建测试数据
        items = [
            {
                "id": 1,
                "region": "国内",
                "layer": "政治",
                "confidence": 0.9,
                "published_at": datetime.now(),
                "source_weight": 1.0,
            },
            {
                "id": 2,
                "region": "国内",
                "layer": "经济",
                "confidence": 0.8,
                "published_at": datetime.now() - timedelta(hours=5),
                "source_weight": 1.0,
            },
            {
                "id": 3,
                "region": "国外",
                "layer": "金融科技",
                "confidence": 0.85,
                "published_at": datetime.now() - timedelta(hours=10),
                "source_weight": 0.8,
            },
        ]

        # 测试分区排序
        sections = section_and_sort(items)

        # 验证分区结构
        assert "国内" in sections
        assert "国外" in sections
        assert "政治" in sections["国内"]
        assert "经济" in sections["国内"]
        assert "金融科技" in sections["国外"]

        # 测试TopN
        topn = select_topn(sections, topn=1)

        # 每个分区应该只有1个
        assert len(topn["国内"]["政治"]) == 1
        assert len(topn["国内"]["经济"]) == 1
        assert len(topn["国外"]["金融科技"]) == 1


class TestBuilderIntegration:
    """测试报告构建器集成功能"""

    def test_builder_functions_work_together(self):
        """测试报告构建器各函数协同工作"""
        from src.composer.builder import (
            generate_overview,
            build_email_body,
            build_attachment,
            build_metadata,
        )

        # 创建测试数据
        sections = {
            "国内": {
                "政治": [
                    {
                        "article_title": "测试标题",
                        "article_url": "https://example.com/1",
                        "fact": "测试事实",
                        "opinion": "测试观点",
                        "region": "国内",
                        "layer": "政治",
                        "source_name": "测试来源",
                        "published_at": datetime.now(),
                        "confidence": 0.85,
                        "score": 0.9,
                    }
                ]
            }
        }

        topn_sections = sections

        # 测试总览生成
        overview = generate_overview(topn_sections)
        assert len(overview) > 0
        assert "1 条" in overview or "1条" in overview

        # 测试HTML生成
        report_date = date.today()
        html_body = build_email_body(report_date, overview, topn_sections)
        assert "测试标题" in html_body
        assert "测试事实" in html_body

        html_attachment = build_attachment(report_date, sections)
        assert "测试事实" in html_attachment

        # 测试元数据生成
        metadata = build_metadata(sections, topn_sections, 100)
        assert metadata["total_items"] == 1
        assert metadata["topn_items"] == 1
        assert metadata["build_time_ms"] == 100


class TestCeleryTaskExecution:
    """测试 Celery 任务执行（简化版）"""

    def test_task_is_registered(self):
        """测试任务已注册"""
        from src.tasks.celery_app import celery_app
        from src.tasks.report_tasks import build_report_task

        # 验证任务已注册
        assert build_report_task.name in celery_app.tasks

    def test_task_has_correct_route(self):
        """测试任务路由正确"""
        from src.tasks.celery_app import celery_app

        # 验证任务路由配置
        task_routes = celery_app.conf.task_routes
        assert "src.tasks.report_tasks.*" in task_routes
        assert task_routes["src.tasks.report_tasks.*"]["queue"] == "report"


class TestBuildReportBatchLogic:
    """测试批量报告构建逻辑"""

    @patch("src.tasks.report_tasks.build_report_task")
    def test_build_report_batch_date_range(self, mock_build_task):
        """测试日期范围生成"""
        from datetime import date

        # 模拟任务成功
        mock_result = MagicMock()
        mock_result.get.return_value = {"status": "success", "report_id": 1}
        mock_build_task.apply.return_value = mock_result

        # 直接调用核心逻辑函数
        result = _build_report_batch_core_logic(
            "2025-11-01",
            "2025-11-03"
        )

        # 验证结果
        assert result["status"] == "success"
        assert result["total"] == 3  # 3天
        assert result["success"] == 3

        # 验证调用了3次任务
        assert mock_build_task.apply.call_count == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
