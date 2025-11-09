"""
去重引擎测试
"""

from datetime import datetime

from src.crawlers.deduplicator import Deduplicator


def test_deduplicate_by_url_removes_duplicates():
    deduplicator = Deduplicator()
    items = [
        {"url": "https://example.com/a", "title": "A"},
        {"url": "https://example.com/b", "title": "B"},
        {"url": "https://example.com/a", "title": "A 重复"},
    ]

    result = deduplicator.deduplicate_by_url(items, existing_urls=set())

    assert len(result) == 2
    assert {item["url"] for item in result} == {
        "https://example.com/a",
        "https://example.com/b",
    }


def test_deduplicate_by_simhash_prefers_unique_content():
    deduplicator = Deduplicator(hamming_threshold=3)

    base_content = "免责声明：以下为测试正文" * 5
    items = [
        {"content_text": base_content, "title": "原文"},
        {"content_text": base_content + "补充", "title": "近似"},
        {"content_text": "完全不同的文章", "title": "不同"},
    ]

    result = deduplicator.deduplicate_by_simhash(items)

    titles = {item["title"] for item in result}
    assert len(result) == 2
    assert "原文" in titles
    assert "不同" in titles


def test_full_deduplicate_generates_dedup_key():
    deduplicator = Deduplicator()

    now = datetime.now()
    items = [
        {
            "url": "https://example.com/a",
            "title": "新闻 A",
            "published_at": now,
            "content_text": "内容 A" * 10,
        },
        {
            "url": "https://example.com/a",
            "title": "新闻 A 重复",
            "published_at": now,
            "content_text": "内容 A" * 10,
        },
    ]

    result = deduplicator.deduplicate(items)

    assert len(result) == 1
    assert "dedup_key" in result[0]
