"""
Tests for BaseCrawler time filtering behaviour.
"""
from datetime import datetime

import pytest
from zoneinfo import ZoneInfo

from src.crawlers.base import BaseCrawler


class DummyCrawler(BaseCrawler):
    """Minimal crawler implementation for testing helper methods."""

    def fetch(self, since=None):
        return []


@pytest.mark.parametrize(
    "since,item_dt,expected",
    [
        # since without tz, item with tz
        (
            datetime(2025, 1, 1, 0, 0),
            datetime(2025, 1, 1, 7, 30, tzinfo=ZoneInfo("Asia/Shanghai")),
            True,
        ),
        # since with tz, item without tz
        (
            datetime(2025, 1, 1, 0, 0, tzinfo=ZoneInfo("Asia/Shanghai")),
            datetime(2025, 1, 1, 0, 30),
            True,
        ),
        # item older than window should be filtered out
        (
            datetime(2025, 1, 1, 0, 0),
            datetime(2024, 12, 31, 20, 0),
            False,
        ),
    ],
)
def test_filter_by_time_handles_mixed_timezone_objects(since, item_dt, expected):
    crawler = DummyCrawler(
        source_id=1,
        source_name="test",
        source_url="https://example.com",
    )

    items = [{"published_at": item_dt, "url": "https://example.com/a"}]

    filtered = crawler.filter_by_time(items, since)
    assert bool(filtered) is expected
