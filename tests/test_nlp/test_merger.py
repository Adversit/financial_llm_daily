"""
抽取结果合并与过滤测试
"""

from src.nlp.merger import (
    deduplicate_facts,
    filter_low_quality_items,
    merge_extraction_results,
    normalize_fact,
    resolve_conflicts,
)


def test_normalize_fact_removes_whitespace_and_symbols():
    text = " 《金融时报》 报道：三 十 亿 "
    normalized = normalize_fact(text)

    assert "30" in normalized
    assert "金融时报" in normalized
    assert " " in normalized


def test_deduplicate_facts_prefers_high_confidence():
    items = [
        {"fact": "人民币升值", "confidence": 0.6},
        {"fact": "人民币升值", "confidence": 0.9},
    ]

    result = deduplicate_facts(items)

    assert len(result) == 1
    assert result[0]["confidence"] == 0.9


def test_resolve_conflicts_fills_unknown_fields():
    items = [
        {"fact": "事件一", "region": "国内", "layer": "政治"},
        {"fact": "事件二", "region": "未知", "layer": "未知"},
    ]

    resolved = resolve_conflicts(items)

    assert resolved[1]["region"] == "国内"
    assert resolved[1]["layer"] == "政治"


def test_merge_extraction_results_combines_and_dedup():
    chunk_results = [
        {"items": [{"fact": "事件一", "confidence": 0.8, "region": "国内", "layer": "政治"}]},
        {"items": [{"fact": "事件一", "confidence": 0.6, "region": "国内", "layer": "政治"}]},
    ]

    merged = merge_extraction_results(chunk_results)

    assert merged["metadata"]["original_count"] == 2
    assert merged["metadata"]["merged_count"] == 1


def test_filter_low_quality_items_applies_thresholds():
    items = [
        {"fact": "高置信度", "confidence": 0.8, "region": "国内", "layer": "经济"},
        {"fact": "低置信度", "confidence": 0.3, "region": "国内", "layer": "经济"},
        {"fact": "太短", "confidence": 0.9, "region": "国内", "layer": "经济"},
    ]

    filtered = filter_low_quality_items(items, min_confidence=0.5, min_fact_length=3)

    assert len(filtered) == 1
    assert filtered[0]["fact"] == "高置信度"
