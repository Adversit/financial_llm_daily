"""
评分器模块测试
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from src.composer.scorer import (
    calculate_score,
    filter_items,
    section_and_sort,
    select_topn,
    get_all_items_sorted,
    get_sections_statistics,
)


class TestCalculateScore:
    """测试评分函数"""

    def test_calculate_score_basic(self):
        """测试基本评分计算"""
        item = {
            "confidence": 0.8,
            "published_at": datetime.now() - timedelta(hours=2),
            "source_weight": 1.0,
        }

        score = calculate_score(item)

        # 验证评分在 0-1 之间
        assert 0 <= score <= 1

        # 验证评分公式：0.5*影响力 + 0.3*新近度 + 0.2*权威
        # 影响力 = 0.8
        # 新近度 = 1 - 2/24 ≈ 0.917
        # 权威 = 1.0
        # 预期分数 ≈ 0.5*0.8 + 0.3*0.917 + 0.2*1.0 ≈ 0.875
        assert 0.8 < score < 0.9

    def test_calculate_score_high_confidence(self):
        """测试高置信度项"""
        item = {
            "confidence": 1.0,
            "published_at": datetime.now(),
            "source_weight": 1.0,
        }

        score = calculate_score(item)

        # 高置信度 + 刚发布 + 权威来源 = 高分
        assert score > 0.9

    def test_calculate_score_low_confidence(self):
        """测试低置信度项"""
        item = {
            "confidence": 0.3,
            "published_at": datetime.now() - timedelta(hours=20),
            "source_weight": 0.5,
        }

        score = calculate_score(item)

        # 低置信度 + 较旧 + 低权威 = 低分
        assert score < 0.5

    def test_calculate_score_old_article(self):
        """测试旧文章的新近度衰减"""
        item1 = {
            "confidence": 0.8,
            "published_at": datetime.now(),
            "source_weight": 1.0,
        }

        item2 = {
            "confidence": 0.8,
            "published_at": datetime.now() - timedelta(hours=23),
            "source_weight": 1.0,
        }

        score1 = calculate_score(item1)
        score2 = calculate_score(item2)

        # 新文章分数应该更高
        assert score1 > score2

    def test_calculate_score_missing_published_at(self):
        """测试缺少发布时间的情况"""
        item = {
            "confidence": 0.8,
            "published_at": None,
            "source_weight": 1.0,
        }

        score = calculate_score(item)

        # 应该使用默认新近度 0.5
        # 0.5*0.8 + 0.3*0.5 + 0.2*1.0 = 0.75
        assert abs(score - 0.75) < 0.01


class TestSectionAndSort:
    """测试分区和排序"""

    def test_section_and_sort_basic(self):
        """测试基本分区排序"""
        items = [
            {
                "region": "国内",
                "layer": "政治",
                "confidence": 0.8,
                "published_at": datetime.now(),
                "source_weight": 1.0,
            },
            {
                "region": "国内",
                "layer": "经济",
                "confidence": 0.9,
                "published_at": datetime.now(),
                "source_weight": 1.0,
            },
            {
                "region": "国外",
                "layer": "政治",
                "confidence": 0.7,
                "published_at": datetime.now(),
                "source_weight": 1.0,
            },
        ]

        sections = section_and_sort(items)

        # 验证分区结构
        assert "国内" in sections
        assert "国外" in sections
        assert "政治" in sections["国内"]
        assert "经济" in sections["国内"]
        assert "政治" in sections["国外"]

        # 验证分区内的数量
        assert len(sections["国内"]["政治"]) == 1
        assert len(sections["国内"]["经济"]) == 1
        assert len(sections["国外"]["政治"]) == 1

        # 验证每项都有 score 字段
        for region in sections.values():
            for layer_items in region.values():
                for item in layer_items:
                    assert "score" in item

    def test_section_and_sort_sorting(self):
        """测试分区内排序"""
        items = [
            {
                "region": "国内",
                "layer": "政治",
                "confidence": 0.6,
                "published_at": datetime.now(),
                "source_weight": 1.0,
            },
            {
                "region": "国内",
                "layer": "政治",
                "confidence": 0.9,
                "published_at": datetime.now(),
                "source_weight": 1.0,
            },
            {
                "region": "国内",
                "layer": "政治",
                "confidence": 0.7,
                "published_at": datetime.now(),
                "source_weight": 1.0,
            },
        ]

        sections = section_and_sort(items)

        politics_items = sections["国内"]["政治"]

        # 验证按评分降序排列
        assert politics_items[0]["confidence"] == 0.9
        assert politics_items[1]["confidence"] == 0.7
        assert politics_items[2]["confidence"] == 0.6

        # 验证评分递减
        assert politics_items[0]["score"] >= politics_items[1]["score"]
        assert politics_items[1]["score"] >= politics_items[2]["score"]

    def test_section_and_sort_empty(self):
        """测试空列表"""
        sections = section_and_sort([])

        assert sections == {}


class TestSelectTopN:
    """测试 TopN 筛选"""

    def test_select_topn_basic(self):
        """测试基本 TopN 筛选"""
        sections = {
            "国内": {
                "政治": [
                    {"score": 0.9},
                    {"score": 0.8},
                    {"score": 0.7},
                    {"score": 0.6},
                    {"score": 0.5},
                    {"score": 0.4},
                    {"score": 0.3},
                ]
            }
        }

        topn_sections = select_topn(sections, topn=5)

        # 验证只保留了前5个
        assert len(topn_sections["国内"]["政治"]) == 5

        # 验证是前5个高分项
        for item in topn_sections["国内"]["政治"]:
            assert item["score"] >= 0.5

    def test_select_topn_less_than_n(self):
        """测试项数少于N的情况"""
        sections = {
            "国内": {
                "政治": [
                    {"score": 0.9},
                    {"score": 0.8},
                ]
            }
        }

        topn_sections = select_topn(sections, topn=5)

        # 验证保留了所有项
        assert len(topn_sections["国内"]["政治"]) == 2

    def test_select_topn_multiple_regions(self):
        """测试多个分区"""
        sections = {
            "国内": {
                "政治": [{"score": i} for i in range(10, 0, -1)],
                "经济": [{"score": i} for i in range(10, 0, -1)],
            },
            "国外": {
                "政治": [{"score": i} for i in range(10, 0, -1)],
            },
        }

        topn_sections = select_topn(sections, topn=3)

        # 验证每个分区都只有3个
        assert len(topn_sections["国内"]["政治"]) == 3
        assert len(topn_sections["国内"]["经济"]) == 3
        assert len(topn_sections["国外"]["政治"]) == 3

    def test_select_topn_empty(self):
        """测试空字典"""
        topn_sections = select_topn({}, topn=5)

        assert topn_sections == {}


class TestGetAllItemsSorted:
    """测试获取所有项排序"""

    def test_get_all_items_sorted(self):
        """测试获取排序后的所有项"""
        sections = {
            "国内": {
                "政治": [
                    {"id": 1, "score": 0.7},
                    {"id": 2, "score": 0.9},
                ],
                "经济": [
                    {"id": 3, "score": 0.6},
                ],
            },
            "国外": {
                "政治": [
                    {"id": 4, "score": 0.8},
                ],
            },
        }

        all_items = get_all_items_sorted(sections)

        # 验证所有项都被收集
        assert len(all_items) == 4

        # 验证按评分降序排列
        assert all_items[0]["id"] == 2  # score 0.9
        assert all_items[1]["id"] == 4  # score 0.8
        assert all_items[2]["id"] == 1  # score 0.7
        assert all_items[3]["id"] == 3  # score 0.6


class TestGetSectionsStatistics:
    """测试获取分区统计"""

    def test_get_sections_statistics(self):
        """测试统计信息生成"""
        sections = {
            "国内": {
                "政治": [1, 2, 3],
                "经济": [4, 5],
            },
            "国外": {
                "政治": [6, 7, 8, 9],
            },
        }

        stats = get_sections_statistics(sections)

        # 验证总数
        assert stats["total_items"] == 9

        # 验证各分区统计
        assert stats["regions"]["国内"]["total"] == 5
        assert stats["regions"]["国内"]["layers"]["政治"] == 3
        assert stats["regions"]["国内"]["layers"]["经济"] == 2

        assert stats["regions"]["国外"]["total"] == 4
        assert stats["regions"]["国外"]["layers"]["政治"] == 4


class TestFilterItems:
    """测试过滤项（需要数据库 mock）"""

    @patch("src.composer.scorer.settings")
    def test_filter_items_mock(self, mock_settings):
        """测试过滤逻辑（使用 mock）"""
        mock_settings.CONFIDENCE_THRESHOLD = 0.6
        mock_settings.MIN_CONTENT_LEN = 120

        # 这个测试需要真实的数据库连接，这里只是示例
        # 实际测试需要使用 pytest fixtures 和测试数据库
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
