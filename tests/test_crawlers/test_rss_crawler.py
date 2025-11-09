"""
RSS 采集器测试
"""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.crawlers.rss_crawler import RSSCrawler


class DummyResponse:
    """简化的响应对象，仅提供 content 属性"""

    def __init__(self, content: bytes):
        self.content = content


class FeedEntry(dict):
    """模拟 feedparser 的条目对象，兼具属性与字典访问"""

    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError as exc:
            raise AttributeError(item) from exc


def _build_feed_entry():
    """构造一个符合解析要求的 RSS 条目"""
    now = datetime.now()
    return FeedEntry(
        title="示例新闻标题",
        link="http://example.com/post-1",
        published_parsed=now.timetuple(),
        content=[{"value": "<p>正文内容</p>"}],
    )


def _mock_feed(entries, bozo=False):
    """构造 feedparser.parse 返回值"""
    return SimpleNamespace(
        bozo=bozo,
        bozo_exception=None,
        entries=entries,
    )


def test_fetch_returns_items(monkeypatch):
    """正常情况下应返回解析后的文章列表"""
    crawler = RSSCrawler(source_id=1, source_name="测试 RSS", source_url="http://feed.example.com")

    # Mock 网络请求与 feed 解析
    monkeypatch.setattr(crawler, "fetch_with_retry", MagicMock(return_value=DummyResponse(b"feed")))
    monkeypatch.setattr(
        "src.crawlers.rss_crawler.feedparser.parse",
        lambda _: _mock_feed([_build_feed_entry()]),
    )

    items = crawler.fetch()

    assert len(items) == 1
    item = items[0]
    assert item["title"] == "示例新闻标题"
    assert item["url"] == "https://example.com/post-1"  # 归一化为 https
    assert item["source_name"] == "测试 RSS"
    assert item["content_text"] == "正文内容"


def test_fetch_handles_failure(monkeypatch):
    """当发生异常时应返回空列表并记录采集结果"""
    crawler = RSSCrawler(source_id=1, source_name="测试 RSS", source_url="http://feed.example.com")

    # 触发异常
    def raise_error(*_args, **_kwargs):
        raise RuntimeError("network error")

    monkeypatch.setattr(crawler, "fetch_with_retry", raise_error)

    items = crawler.fetch()

    assert items == []
