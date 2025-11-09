"""
静态站点采集器测试
"""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from src.crawlers import static_crawler
from src.crawlers.static_crawler import SITE_RULES, SiteRule, StaticCrawler


class DummyResponse:
    """简化的响应对象，仅提供 text 属性"""

    def __init__(self, text: str):
        self.text = text


LIST_HTML = """
<html>
  <body>
    <article><a href="/post-1">文章一</a></article>
    <article><a href="https://example.com/post-2">文章二</a></article>
  </body>
</html>
"""


ARTICLE_HTML = """
<html>
  <head>
    <meta property="article:published_time" content="2025-11-05T06:00:00+08:00" />
    <title>文章标题 | 示例站点</title>
  </head>
  <body>
    <div class="content"><p>正文内容</p></div>
  </body>
</html>
"""


def test_fetch_collects_articles(monkeypatch):
    """应能解析列表页并调用文章采集"""
    monkeypatch.setitem(
        SITE_RULES,
        "example.com",
        SiteRule(
            list_selectors=["article a[href]"],
            allow_patterns=[],
            allowed_domains=["example.com"],
            max_links=10,
        ),
    )

    crawler = StaticCrawler(source_id=2, source_name="静态站点", source_url="https://example.com")

    # 列表页请求
    monkeypatch.setattr(
        crawler,
        "fetch_with_retry",
        MagicMock(return_value=DummyResponse(LIST_HTML)),
    )

    article_data = {
        "title": "文章一",
        "url": "https://example.com/post-1",
        "published_at": datetime.now(),
        "content_text": "正文" * 100,
        "source_name": "静态站点",
    }

    article_data_2 = {
        "title": "文章二",
        "url": "https://example.com/post-2",
        "published_at": datetime.now(),
        "content_text": "正文" * 120,
        "source_name": "静态站点",
    }

    monkeypatch.setattr(
        crawler,
        "_fetch_article",
        MagicMock(side_effect=[article_data, article_data_2]),
    )

    items = crawler.fetch()

    assert len(items) == 2
    urls = {item["url"] for item in items}
    assert urls == {"https://example.com/post-1", "https://example.com/post-2"}


def test_fetch_article_parses_metadata(monkeypatch):
    """应正确解析文章详情页的标题、时间与正文"""
    monkeypatch.setitem(
        SITE_RULES,
        "example.com",
        SiteRule(
            list_selectors=["article a[href]"],
            allow_patterns=[],
            allowed_domains=["example.com"],
        ),
    )

    crawler = StaticCrawler(source_id=2, source_name="静态站点", source_url="https://example.com")

    # 模拟请求文章详情
    monkeypatch.setattr(
        crawler,
        "fetch_with_retry",
        MagicMock(return_value=DummyResponse(ARTICLE_HTML)),
    )

    # 避免依赖真实正文提取逻辑，返回足够长的内容
    monkeypatch.setattr(
        "src.crawlers.static_crawler.extract_main_text",
        lambda _html, _url: "主要内容" * 100,
    )

    item = crawler._fetch_article("https://example.com/post-1")

    assert item is not None
    assert item["title"] == "文章标题"
    assert item["url"] == "https://example.com/post-1"
    assert item["source_name"] == "静态站点"
    assert len(item["content_text"]) >= 100
    assert item["published_at"].year == 2025


def test_fetch_uses_rss_mode(monkeypatch):
    """站点配置为 RSS 时应调用 RSSCrawler"""
    rss_calls = {"fetch": 0}

    class DummyRSSCrawler:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        def fetch(self, since=None):
            rss_calls["fetch"] += 1
            return [
                {
                    "title": "RSS 文章",
                    "url": "https://rss.example.com/post",
                    "content_text": "内容" * 50,
                    "source_name": "RSS 站点",
                    "published_at": datetime.now(),
                }
            ]

    monkeypatch.setitem(
        SITE_RULES,
        "rss.example.com",
        SiteRule(mode="rss", rss_url="https://rss.example.com/feed.xml"),
    )
    monkeypatch.setattr(static_crawler, "RSSCrawler", DummyRSSCrawler)

    crawler = StaticCrawler(
        source_id=10,
        source_name="RSS 站点",
        source_url="https://rss.example.com",
        parser="rss.example.com",
    )

    items = crawler.fetch()

    assert rss_calls["fetch"] == 1
    assert len(items) == 1
    assert items[0]["title"] == "RSS 文章"
