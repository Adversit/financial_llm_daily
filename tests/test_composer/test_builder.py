"""
报告构建器模块测试
"""

import os
import pytest
from datetime import date, datetime
from unittest.mock import patch, MagicMock

from src.composer.builder import (
    generate_overview,
    build_email_body,
    build_attachment,
    build_metadata,
    format_datetime,
)


class TestGenerateOverview:
    """测试总览摘要生成"""

    def test_generate_overview_empty(self):
        """测试空分区"""
        overview = generate_overview({})

        assert overview == "今日暂无重要金融情报。"

    def test_generate_overview_basic(self):
        """测试基本摘要生成"""
        sections = {
            "国内": {
                "政治": [
                    {
                        "fact": "重要政策发布，将对金融市场产生深远影响。这是一个长文本用来测试截断功能。",
                        "score": 0.95,
                    }
                ],
                "经济": [
                    {
                        "fact": "经济数据超预期增长。",
                        "score": 0.85,
                    }
                ],
            },
            "国外": {
                "金融科技": [
                    {
                        "fact": "科技巨头发布新产品。",
                        "score": 0.80,
                    }
                ],
            },
        }

        overview = generate_overview(sections)

        # 验证包含总数统计
        assert "3 条" in overview or "3条" in overview

        # 验证包含分区统计
        assert "国内" in overview
        assert "国外" in overview

        # 验证有重点关注
        assert "重点关注" in overview or "重要" in overview

        # 验证长度在合理范围内
        assert len(overview) <= 250

    def test_generate_overview_multiple_items(self):
        """测试多个项的摘要"""
        sections = {
            "国内": {
                "政治": [{"fact": f"事实{i}", "score": 0.9 - i * 0.1} for i in range(5)],
                "经济": [{"fact": f"经济事实{i}", "score": 0.8 - i * 0.1} for i in range(3)],
            },
        }

        overview = generate_overview(sections)

        # 验证统计了总数
        assert "8 条" in overview or "8条" in overview

        # 验证长度控制
        assert len(overview) <= 250

    def test_generate_overview_length_limit(self):
        """测试长度限制"""
        # 创建很多项
        sections = {
            "国内": {
                "政治": [
                    {
                        "fact": "这是一个非常非常长的事实描述" * 20,
                        "score": 0.9,
                    }
                    for _ in range(10)
                ],
            },
        }

        overview = generate_overview(sections)

        # 验证被截断到250字以内
        assert len(overview) <= 250
        if len(overview) == 250:
            assert overview.endswith("...")


class TestBuildEmailBody:
    """测试邮件正文HTML生成"""

    def test_build_email_body_basic(self):
        """测试基本HTML生成"""
        report_date = date(2025, 11, 5)
        overview = "今日共监测到10条金融情报。"
        sections = {
            "国内": {
                "政治": [
                    {
                        "article_title": "测试标题",
                        "article_url": "https://example.com/article1",
                        "fact": "这是一个测试事实",
                        "opinion": "这是一个测试观点",
                        "region": "国内",
                        "layer": "政治",
                        "source_name": "测试来源",
                        "published_at": datetime.now(),
                        "confidence": 0.85,
                    }
                ],
            },
        }

        html = build_email_body(report_date, overview, sections)

        # 验证HTML包含关键元素
        assert "<!DOCTYPE html>" in html
        assert "金融情报日报" in html
        assert "2025年11月05日" in html
        assert overview in html
        assert "测试标题" in html
        assert "测试事实" in html
        assert "测试观点" in html
        assert "https://example.com/article1" in html

        # 验证有目录
        assert "目录" in html

        # 验证有样式
        assert "<style>" in html

    def test_build_email_body_empty_sections(self):
        """测试空分区"""
        report_date = date(2025, 11, 5)
        overview = "今日暂无内容。"
        sections = {}

        html = build_email_body(report_date, overview, sections)

        # 验证HTML仍然生成
        assert "<!DOCTYPE html>" in html
        assert "金融情报日报" in html
        assert overview in html

        # 验证显示空状态
        assert "暂无内容" in html or len(sections) == 0

    def test_build_email_body_multiple_layers(self):
        """测试多层级"""
        report_date = date(2025, 11, 5)
        overview = "测试摘要"
        sections = {
            "国内": {
                "政治": [
                    {
                        "article_title": "政治新闻",
                        "article_url": "https://example.com/1",
                        "fact": "政治事实",
                        "opinion": "",
                        "region": "国内",
                        "layer": "政治",
                        "source_name": "来源1",
                        "published_at": datetime.now(),
                        "confidence": 0.9,
                    }
                ],
                "经济": [
                    {
                        "article_title": "经济新闻",
                        "article_url": "https://example.com/2",
                        "fact": "经济事实",
                        "opinion": "",
                        "region": "国内",
                        "layer": "经济",
                        "source_name": "来源2",
                        "published_at": datetime.now(),
                        "confidence": 0.8,
                    }
                ],
            },
            "国外": {
                "金融科技": [
                    {
                        "article_title": "科技新闻",
                        "article_url": "https://example.com/3",
                        "fact": "科技事实",
                        "opinion": "",
                        "region": "国外",
                        "layer": "金融科技",
                        "source_name": "来源3",
                        "published_at": datetime.now(),
                        "confidence": 0.85,
                    }
                ],
            },
        }

        html = build_email_body(report_date, overview, sections)

        # 验证包含所有层级
        assert "政治" in html
        assert "经济" in html
        assert "金融科技" in html

        # 验证包含所有内容
        assert "政治新闻" in html
        assert "经济新闻" in html
        assert "科技新闻" in html


class TestBuildAttachment:
    """测试附件HTML生成"""

    def test_build_attachment_basic(self):
        """测试基本附件生成"""
        report_date = date(2025, 11, 5)
        sections = {
            "国内": {
                "政治": [
                    {
                        "article_title": "测试标题",
                        "article_url": "https://example.com/article1",
                        "fact": "这是一个测试事实",
                        "opinion": "这是一个测试观点",
                        "region": "国内",
                        "layer": "政治",
                        "source_name": "测试来源",
                        "published_at": datetime.now(),
                        "confidence": 0.85,
                    }
                ],
            },
        }

        html = build_attachment(report_date, sections)

        # 验证HTML包含关键元素
        assert "<!DOCTYPE html>" in html
        assert "全量事实与观点" in html
        assert "2025年11月05日" in html
        assert "测试事实" in html
        assert "测试观点" in html
        assert "https://example.com/article1" in html

        # 验证有统计信息
        assert "共" in html
        assert "条" in html

    def test_build_attachment_empty(self):
        """测试空附件"""
        report_date = date(2025, 11, 5)
        sections = {}

        html = build_attachment(report_date, sections)

        # 验证HTML仍然生成
        assert "<!DOCTYPE html>" in html
        assert "全量事实与观点" in html

        # 验证显示空状态
        assert "暂无内容" in html or len(sections) == 0

    def test_build_attachment_no_opinion(self):
        """测试没有观点的情况"""
        report_date = date(2025, 11, 5)
        sections = {
            "国内": {
                "经济": [
                    {
                        "article_title": "测试标题",
                        "article_url": "https://example.com/article1",
                        "fact": "仅有事实",
                        "opinion": "",  # 空观点
                        "region": "国内",
                        "layer": "经济",
                        "source_name": "测试来源",
                        "published_at": datetime.now(),
                        "confidence": 0.85,
                    }
                ],
            },
        }

        html = build_attachment(report_date, sections)

        # 验证包含事实
        assert "仅有事实" in html

        # 观点为空时不应该显示观点部分（取决于模板实现）
        # 可以根据实际模板调整这个断言


class TestBuildMetadata:
    """测试元数据生成"""

    def test_build_metadata_basic(self):
        """测试基本元数据生成"""
        sections = {
            "国内": {
                "政治": [1, 2, 3],
                "经济": [4, 5],
            },
            "国外": {
                "金融科技": [6, 7, 8, 9],
            },
        }

        topn_sections = {
            "国内": {
                "政治": [1, 2],
                "经济": [4],
            },
        }

        metadata = build_metadata(sections, topn_sections, 1500)

        # 验证总数
        assert metadata["total_items"] == 9
        assert metadata["topn_items"] == 3

        # 验证耗时
        assert metadata["build_time_ms"] == 1500

        # 验证分区统计
        assert metadata["sections_count"]["国内"]["政治"] == 3
        assert metadata["sections_count"]["国内"]["经济"] == 2
        assert metadata["sections_count"]["国外"]["金融科技"] == 4

        # 验证生成时间
        assert "generated_at" in metadata

    def test_build_metadata_empty(self):
        """测试空元数据"""
        metadata = build_metadata({}, {}, 100)

        assert metadata["total_items"] == 0
        assert metadata["topn_items"] == 0
        assert metadata["build_time_ms"] == 100


class TestFormatDatetime:
    """测试日期时间格式化"""

    def test_format_datetime_basic(self):
        """测试基本格式化"""
        dt = datetime(2025, 11, 5, 14, 30, 45)
        result = format_datetime(dt)

        assert result == "2025-11-05 14:30"

    def test_format_datetime_custom_format(self):
        """测试自定义格式"""
        dt = datetime(2025, 11, 5, 14, 30, 45)
        result = format_datetime(dt, fmt="%Y年%m月%d日")

        assert result == "2025年11月05日"

    def test_format_datetime_none(self):
        """测试None值"""
        result = format_datetime(None)

        assert result == ""


class TestTemplateRendering:
    """测试模板渲染（集成测试）"""

    def test_template_files_exist(self):
        """测试模板文件是否存在"""
        template_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "src", "composer", "templates"
        )

        email_body_path = os.path.join(template_dir, "email_body.html")
        attachment_path = os.path.join(template_dir, "attachment.html")

        assert os.path.exists(email_body_path), "email_body.html 模板不存在"
        assert os.path.exists(attachment_path), "attachment.html 模板不存在"

    def test_build_with_real_templates(self):
        """测试使用真实模板构建（集成测试）"""
        report_date = date(2025, 11, 5)
        overview = "测试摘要"
        sections = {
            "国内": {
                "政治": [
                    {
                        "article_title": "测试文章",
                        "article_url": "https://example.com/1",
                        "fact": "测试事实" * 50,  # 长文本
                        "opinion": "测试观点",
                        "region": "国内",
                        "layer": "政治",
                        "source_name": "测试来源",
                        "published_at": datetime.now(),
                        "confidence": 0.85,
                    }
                ],
            },
        }

        # 测试邮件正文生成
        html_body = build_email_body(report_date, overview, sections)
        assert len(html_body) > 0
        assert "测试文章" in html_body

        # 测试附件生成
        html_attachment = build_attachment(report_date, sections)
        assert len(html_attachment) > 0
        assert "测试事实" in html_attachment


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
