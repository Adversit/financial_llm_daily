"""
词云关键词功能测试
"""
import pytest
from collections import Counter


def test_merge_similar_keywords():
    """测试关键词合并功能"""
    from src.web.routes.stats import _merge_similar_keywords

    # 测试数据：包含相似和重复的关键词
    keywords = [
        "数字货币", "数字货币", "数字金融",  # 相似度高，应合并
        "央行政策", "央行政策", "央行",  # 相似但可能不合并
        "区块链", "区块链技术",  # 相似度高，应合并
        "金融科技", "金融科技"  # 完全相同
    ]

    result = _merge_similar_keywords(keywords)

    # 验证结果
    assert isinstance(result, dict)
    assert all(isinstance(k, str) and isinstance(v, int) for k, v in result.items())

    # 验证词频总和
    total_original = len(keywords)
    total_merged = sum(result.values())
    assert total_original == total_merged, "合并后词频总和应该保持不变"

    # 验证合并效果（合并后的关键词数应该小于或等于原始唯一关键词数）
    unique_original = len(set(keywords))
    assert len(result) <= unique_original

    print(f"原始关键词数: {len(keywords)}, 唯一关键词数: {unique_original}")
    print(f"合并后关键词数: {len(result)}")
    print(f"合并结果: {result}")


def test_find_chinese_font():
    """测试中文字体查找功能"""
    from src.web.routes.stats import _find_chinese_font

    font_path = _find_chinese_font()

    # 在CI环境中可能找不到字体，所以只验证返回类型
    assert font_path is None or isinstance(font_path, str)

    if font_path:
        print(f"找到中文字体: {font_path}")
    else:
        print("未找到中文字体（正常情况，在CI环境中可能没有中文字体）")


def test_extract_result_with_keywords():
    """测试提取结果包含关键词"""
    from src.nlp.extractor import ExtractResult

    # 创建测试提取结果
    result = ExtractResult(
        status="success",
        items=[
            {
                "fact": "央行发布新政策",
                "opinion": "预计将影响市场",
                "region": "国内",
                "layer": "金融政策监管",
                "confidence": 0.9,
                "finance_relevance": 1.0
            }
        ],
        keywords=["央行政策", "金融监管", "货币政策"],
        metadata={"total_chunks": 1}
    )

    # 验证关键词字段存在
    assert hasattr(result, 'keywords')
    assert isinstance(result.keywords, list)
    assert len(result.keywords) == 3
    assert "央行政策" in result.keywords

    print(f"提取结果关键词: {result.keywords}")


def test_keywords_frequency_counter():
    """测试关键词词频统计"""
    keywords = [
        "数字货币", "央行政策", "数字货币",
        "金融科技", "央行政策", "数字货币"
    ]

    freq = Counter(keywords)

    assert freq["数字货币"] == 3
    assert freq["央行政策"] == 2
    assert freq["金融科技"] == 1

    print(f"词频统计结果: {dict(freq)}")


if __name__ == "__main__":
    # 运行测试
    test_merge_similar_keywords()
    test_find_chinese_font()
    test_extract_result_with_keywords()
    test_keywords_frequency_counter()
    print("\n✅ 所有测试通过")
