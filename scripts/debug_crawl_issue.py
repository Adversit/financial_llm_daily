"""
调试采集任务中的 source_id 缺失问题

用于定位 crawl_tasks 中 KeyError: 'source_id' 的根本原因
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import timedelta
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from src.config.settings import settings
from src.db.session import get_db
from src.models.source import Source, SourceType
from src.models.article import Article
from src.crawlers.rss_crawler import RSSCrawler
from src.crawlers.deduplicator import Deduplicator
from src.utils.time_utils import get_local_now
from src.utils.logger import logger


def test_rss_crawler_output():
    """测试 RSS 采集器的原始输出"""
    logger.info("=" * 60)
    logger.info("测试 1: RSS 采集器原始输出")
    logger.info("=" * 60)

    db: Session = next(get_db())

    try:
        # 获取第一个 RSS 源
        source = db.query(Source).filter(
            Source.type == SourceType.RSS,
            Source.enabled == True
        ).first()

        if not source:
            logger.error("未找到启用的 RSS 源")
            return

        logger.info(f"测试源: {source.name} (ID: {source.id})")
        logger.info(f"URL: {source.url}")

        # 创建采集器
        crawler = RSSCrawler(
            source_id=source.id,
            source_name=source.name,
            source_url=source.url,
            parser=source.parser
        )
        since = get_local_now() - timedelta(hours=24)

        # 采集
        items = crawler.fetch(since=since)
        logger.info(f"采集到 {len(items)} 篇文章")

        # 检查前3篇文章的结构
        for i, item in enumerate(items[:3], 1):
            logger.info(f"\n--- 文章 {i} ---")
            logger.info(f"类型: {type(item)}")

            if isinstance(item, dict):
                logger.info(f"字段: {list(item.keys())}")
                logger.info(f"source_id 存在: {'source_id' in item}")
                logger.info(f"source_id 值: {item.get('source_id', 'NOT_FOUND')}")
                logger.info(f"title: {item.get('title', 'N/A')[:50]}")
                logger.info(f"content_text 长度: {len(item.get('content_text', '') or '')}")
            else:
                logger.info(f"对象属性: {dir(item)}")
                if hasattr(item, '__dict__'):
                    logger.info(f"__dict__: {vars(item)}")

        return items

    finally:
        db.close()


def test_normalize_items(raw_items: List[Any]):
    """测试规范化处理"""
    logger.info("\n" + "=" * 60)
    logger.info("测试 2: 规范化处理")
    logger.info("=" * 60)

    db: Session = next(get_db())

    try:
        source = db.query(Source).filter(
            Source.type == SourceType.RSS,
            Source.enabled == True
        ).first()

        # 模拟 _normalize_crawl_items
        from collections.abc import Mapping

        normalized: List[Dict] = []

        for idx, raw in enumerate(raw_items[:3], 1):
            logger.info(f"\n--- 处理文章 {idx} ---")
            item: Dict[str, Any] = None

            if isinstance(raw, Mapping):
                item = dict(raw)
                logger.info("✓ 识别为 Mapping，转为 dict")
            elif hasattr(raw, "__dict__"):
                item = {k: v for k, v in vars(raw).items() if not k.startswith("_")}
                logger.info("✓ 识别为对象，提取 __dict__")

            if item is None:
                logger.warning(f"✗ 未知类型: {type(raw)}")
                continue

            logger.info(f"处理前字段: {list(item.keys())}")
            logger.info(f"处理前 source_id: {item.get('source_id', 'NOT_FOUND')}")

            # 补齐来源信息
            item.setdefault("source_id", source.id)
            item.setdefault("source_name", source.name)

            logger.info(f"处理后字段: {list(item.keys())}")
            logger.info(f"处理后 source_id: {item.get('source_id', 'NOT_FOUND')}")
            logger.info(f"source_id 值类型: {type(item.get('source_id'))}")
            logger.info(f"source_id == source.id: {item.get('source_id') == source.id}")

            # canonical_url 回落
            canonical_url = item.get("canonical_url") or item.get("url")
            if canonical_url:
                item["canonical_url"] = canonical_url

            normalized.append(item)

        logger.info(f"\n规范化完成: {len(raw_items)} -> {len(normalized)}")
        return normalized

    finally:
        db.close()


def test_deduplicator(normalized_items: List[Dict]):
    """测试去重器"""
    logger.info("\n" + "=" * 60)
    logger.info("测试 3: 去重处理")
    logger.info("=" * 60)

    db: Session = next(get_db())

    try:
        # 加载已有数据
        existing_urls = {
            url for (url,) in db.query(Article.url).filter(Article.url.isnot(None))
        }
        existing_hashes = [
            simhash for (simhash,) in db.query(Article.simhash).filter(Article.simhash.isnot(None))
        ]

        logger.info(f"已有 URL 数量: {len(existing_urls)}")
        logger.info(f"已有 SimHash 数量: {len(existing_hashes)}")

        # 去重前检查
        logger.info("\n去重前检查:")
        for idx, item in enumerate(normalized_items[:3], 1):
            logger.info(f"文章 {idx}: source_id={item.get('source_id')}, keys={list(item.keys())}")

        # 执行去重
        deduplicator = Deduplicator()
        deduped_items = deduplicator.deduplicate(
            normalized_items[:3],  # 只处理前3篇
            existing_urls=existing_urls,
            existing_hashes=existing_hashes
        )

        # 去重后检查
        logger.info(f"\n去重后数量: {len(normalized_items[:3])} -> {len(deduped_items)}")

        for idx, item in enumerate(deduped_items, 1):
            logger.info(f"\n--- 去重后文章 {idx} ---")
            logger.info(f"字段: {list(item.keys())}")
            logger.info(f"source_id 存在: {'source_id' in item}")
            logger.info(f"source_id 值: {item.get('source_id', 'NOT_FOUND')}")
            logger.info(f"source_name: {item.get('source_name', 'NOT_FOUND')}")
            logger.info(f"title: {item.get('title', 'N/A')[:50]}")
            logger.info(f"simhash: {item.get('simhash', 'NOT_FOUND')}")
            logger.info(f"dedup_key: {item.get('dedup_key', 'NOT_FOUND')[:50] if item.get('dedup_key') else 'NOT_FOUND'}")

        return deduped_items

    finally:
        db.close()


def test_prepare_for_storage(deduped_items: List[Dict]):
    """测试存储准备"""
    logger.info("\n" + "=" * 60)
    logger.info("测试 4: 存储准备")
    logger.info("=" * 60)

    deduplicator = Deduplicator()

    # 检查 dedup_key 是否已存在
    for idx, item in enumerate(deduped_items, 1):
        logger.info(f"\n--- 文章 {idx} ---")
        logger.info(f"准备前 dedup_key: {item.get('dedup_key', 'NOT_FOUND')}")

        if "dedup_key" not in item:
            item["dedup_key"] = deduplicator.generate_dedup_key(item)
            logger.info(f"✓ 生成 dedup_key: {item['dedup_key'][:50]}")
        else:
            logger.info(f"✓ dedup_key 已存在")

        # 最终字段检查
        logger.info(f"最终字段: {list(item.keys())}")
        logger.info(f"source_id: {item.get('source_id', 'NOT_FOUND')}")

    return deduped_items


def test_store_articles(final_items: List[Dict]):
    """测试存储逻辑（模拟）"""
    logger.info("\n" + "=" * 60)
    logger.info("测试 5: 存储逻辑（模拟，不实际写入）")
    logger.info("=" * 60)

    db: Session = next(get_db())

    try:
        source = db.query(Source).filter(
            Source.type == SourceType.RSS,
            Source.enabled == True
        ).first()

        existing_urls = {
            url for (url,) in db.query(Article.url).filter(Article.url.isnot(None))
        }

        from collections.abc import Mapping

        # 模拟 _store_articles 的前半部分
        normalized_items: List[Dict] = []

        for raw in final_items:
            if isinstance(raw, Mapping):
                normalized_items.append(dict(raw))
            else:
                logger.warning(f"未知采集项类型: type={type(raw)}")

        logger.info(f"转换为 normalized_items: {len(normalized_items)} 个")

        # 遍历存储
        for idx, item in enumerate(normalized_items, 1):
            logger.info(f"\n--- 准备存储文章 {idx} ---")

            # 关键逻辑：获取 source_id
            logger.info(f"item 类型: {type(item)}")
            logger.info(f"item 字段: {list(item.keys())}")
            logger.info(f"'source_id' in item: {'source_id' in item}")

            # 尝试不同的访问方式
            try:
                # 方式1: .get() 带默认值
                source_id_1 = item.get("source_id", source.id)
                logger.info(f"✓ .get('source_id', default): {source_id_1}")
            except Exception as e:
                logger.error(f"✗ .get('source_id', default) 失败: {e}")

            try:
                # 方式2: 直接访问
                source_id_2 = item["source_id"]
                logger.info(f"✓ item['source_id']: {source_id_2}")
            except KeyError as e:
                logger.error(f"✗ item['source_id'] KeyError: {e}")
            except Exception as e:
                logger.error(f"✗ item['source_id'] 其他错误: {e}")

            try:
                # 方式3: 检查后访问
                if "source_id" not in item:
                    logger.warning(f"source_id 不存在，使用默认: {source.id}")
                    source_id_3 = source.id
                else:
                    source_id_3 = item["source_id"]
                logger.info(f"✓ 检查后访问: {source_id_3}")
            except Exception as e:
                logger.error(f"✗ 检查后访问失败: {e}")

            # 检查其他必需字段
            url = item.get("url")
            if not url:
                logger.warning(f"URL 为空，跳过")
                continue

            if url in existing_urls:
                logger.info(f"URL 已存在，跳过: {url}")
                continue

            logger.info(f"✓ 该文章可以存储")
            logger.info(f"  - source_id: {item.get('source_id')}")
            logger.info(f"  - title: {item.get('title', '')[:50]}")
            logger.info(f"  - url: {url[:80]}")

    finally:
        db.close()


def main():
    """主测试流程"""
    logger.info("🔍 开始调试采集任务 source_id 缺失问题\n")

    # 测试1: 采集器原始输出
    raw_items = test_rss_crawler_output()
    if not raw_items:
        logger.error("❌ 采集失败，无法继续测试")
        return

    # 测试2: 规范化处理
    normalized_items = test_normalize_items(raw_items)
    if not normalized_items:
        logger.error("❌ 规范化失败，无法继续测试")
        return

    # 测试3: 去重处理
    deduped_items = test_deduplicator(normalized_items)
    if not deduped_items:
        logger.warning("⚠️ 去重后无文章，可能全部重复")
        return

    # 测试4: 存储准备
    final_items = test_prepare_for_storage(deduped_items)

    # 测试5: 存储逻辑（模拟）
    test_store_articles(final_items)

    logger.info("\n" + "=" * 60)
    logger.info("✅ 所有测试完成")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
