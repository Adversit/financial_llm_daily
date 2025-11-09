"""
静态信息源采集测试脚本

用于手动验证特定站点的采集效果，便于在调整解析规则后快速回归。

用法（需在激活虚拟环境、网络可访问时运行）:

    poetry run python scripts/test_static_sources.py
    poetry run python scripts/test_static_sources.py --since-hours 48
    poetry run python scripts/test_static_sources.py --sources openai.com blog.google
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from typing import Iterable, List, Optional

from loguru import logger

from src.crawlers.static_crawler import StaticCrawler

DEFAULT_SOURCES = [
    ("OpenAI", "https://openai.com/news", "openai.com"),
    ("Google Blog", "https://blog.google", "blog.google"),
    ("Anthropic", "https://www.anthropic.com/news", "anthropic.com"),
    ("xAI", "https://x.ai/news", "x.ai"),
    ("NVIDIA News", "https://www.nvidia.com/en-us/news", "nvidia.com"),
    ("Microsoft AI Blog", "https://www.microsoft.com/en-us/ai/blog", "microsoft.com"),
    ("Finextra Research", "https://www.finextra.com/news", "finextra.com"),
    ("Savanta", "https://savanta.com/industries/financial-services", "savanta.com"),
    ("IDC", "https://www.idc.com/about/rss", "idc.com"),
]


def iter_sources(
    selected_parsers: Optional[Iterable[str]] = None,
) -> Iterable[tuple[str, str, str]]:
    """根据用户选择返回需要测试的站点"""
    if not selected_parsers:
        yield from DEFAULT_SOURCES
        return

    selected = {parser.lower() for parser in selected_parsers}
    for name, url, parser in DEFAULT_SOURCES:
        if parser.lower() in selected:
            yield name, url, parser


def run_test_for_source(
    name: str,
    url: str,
    parser: str,
    since_hours: int,
    max_items: int,
) -> dict:
    """执行单个站点的采集测试"""
    crawler = StaticCrawler(
        source_id=0,
        source_name=name,
        source_url=url,
        parser=parser,
    )

    since = datetime.utcnow() - timedelta(hours=since_hours)
    logger.info("=" * 80)
    logger.info(f"开始采集: {name} ({url})  parser={parser}, since={since}")

    items = crawler.fetch(since=since)
    if max_items and len(items) > max_items:
        items = items[:max_items]

    for idx, item in enumerate(items, start=1):
        published = item.get("published_at")
        published_str = published.isoformat() if isinstance(published, datetime) else str(published)
        logger.info(
            f"[{name}] #{idx:02d} {item.get('title', '无标题')}  "
            f"published_at={published_str}  url={item.get('url')}"
        )

    summary = {
        "name": name,
        "url": url,
        "parser": parser,
        "total": len(items),
    }
    logger.success(f"{name} 采集完成，共获取 {len(items)} 篇文章")
    return summary


def main():
    parser = argparse.ArgumentParser(description="静态信息源采集测试")
    parser.add_argument(
        "--sources",
        nargs="*",
        metavar="PARSER",
        help="仅测试指定 parser 的站点（默认为全部）。例: openai.com blog.google",
    )
    parser.add_argument(
        "--since-hours",
        type=int,
        default=24,
        help="仅保留过去 N 小时内的文章（默认 24 小时）",
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=10,
        help="每个站点最多打印的文章数量（默认 10，设为 0 表示不限制）",
    )

    args = parser.parse_args()

    selected_sources = list(iter_sources(args.sources))
    if not selected_sources:
        logger.error("未匹配到任何站点，请检查 --sources 参数")
        return

    results: List[dict] = []
    for name, url, parser_name in selected_sources:
        try:
            summary = run_test_for_source(
                name=name,
                url=url,
                parser=parser_name,
                since_hours=args.since_hours,
                max_items=args.max_items,
            )
            results.append(summary)
        except Exception as exc:
            logger.exception(f"{name} 采集测试失败: {exc}")

    logger.info("=" * 80)
    logger.info("采集测试汇总:")
    for summary in results:
        logger.info(
            f"- {summary['name']}: {summary['total']} 篇  ({summary['url']})  parser={summary['parser']}"
        )


if __name__ == "__main__":
    main()
