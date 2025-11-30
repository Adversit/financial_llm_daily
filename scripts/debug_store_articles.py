"""
精确定位 _store_articles 中的 KeyError

在 _store_articles 的每个步骤都添加日志
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import timedelta
from typing import List, Dict, Tuple
from collections.abc import Mapping
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from src.config.settings import settings
from src.db.session import get_db
from src.models.source import Source, SourceType
from src.models.article import Article, ProcessingStatus
from src.models.extraction import ExtractionQueue, QueueStatus
from src.crawlers.rss_crawler import RSSCrawler
from src.crawlers.deduplicator import Deduplicator
from src.utils.time_utils import get_local_now, to_local_naive
from src.utils.logger import logger


def debug_store_articles(
    db: Session,
    items: List[Dict],
    source: Source,
    existing_urls: set,
) -> Tuple[int, int]:
    """
    调试版的 _store_articles，添加详细日志
    """
    saved_count = 0
    queued_count = 0

    logger.info(f"=" * 80)
    logger.info(f"开始存储，输入 {len(items)} 个 items")
    logger.info(f"=" * 80)

    normalized_items: List[Dict] = []

    # 步骤1: 规范化
    logger.info(f"\n步骤 1: 规范化 items")
    for idx, raw in enumerate(items, 1):
        logger.info(f"  - 处理 item {idx}/{len(items)}: type={type(raw)}")

        if isinstance(raw, Mapping):
            normalized_items.append(dict(raw))
            logger.info(f"    ✓ 转为 dict")
        else:
            logger.warning(f"    ✗ 未知类型，跳过: type={type(raw)}")

    logger.info(f"规范化完成: {len(items)} -> {len(normalized_items)}")

    # 步骤2: 遍历存储
    logger.info(f"\n步骤 2: 遍历存储")

    for idx, item in enumerate(normalized_items, 1):
        logger.info(f"\n--- 处理文章 {idx}/{len(normalized_items)} ---")

        # 2.1 检查字典结构
        logger.info(f"字典类型: {type(item)}")
        logger.info(f"字典字段: {list(item.keys())}")

        # 2.2 获取 source_id
        logger.info(f"尝试获取 source_id...")
        try:
            logger.info(f"  - 'source_id' in item: {'source_id' in item}")
            logger.info(f"  - item.get('source_id'): {item.get('source_id')}")
            logger.info(f"  - source.id: {source.id}")

            source_id = item.get("source_id", source.id)
            logger.info(f"  ✓ source_id = {source_id}")

            if "source_id" not in item:
                logger.warning(f"  ⚠️ source_id 不在 item 中，使用默认值")
        except Exception as e:
            logger.error(f"  ✗ 获取 source_id 失败: {e}", exc_info=True)
            raise

        # 2.3 获取 source_name
        logger.info(f"尝试获取 source_name...")
        try:
            source_name = item.get("source_name", source.name)
            logger.info(f"  ✓ source_name = {source_name}")
        except Exception as e:
            logger.error(f"  ✗ 获取 source_name 失败: {e}", exc_info=True)
            raise

        # 2.4 获取 url
        logger.info(f"尝试获取 url...")
        try:
            url = item.get("url")
            logger.info(f"  ✓ url = {url[:80] if url else None}")

            if not url:
                logger.warning(f"  ⚠️ URL 为空，跳过")
                continue

            if url in existing_urls:
                logger.info(f"  ⚠️ URL 已存在，跳过")
                continue
        except Exception as e:
            logger.error(f"  ✗ 获取 url 失败: {e}", exc_info=True)
            raise

        # 2.5 获取 published_at
        logger.info(f"尝试获取 published_at...")
        try:
            published_at = item.get("published_at")
            if published_at:
                published_at = to_local_naive(published_at)
            logger.info(f"  ✓ published_at = {published_at}")
        except Exception as e:
            logger.error(f"  ✗ 获取 published_at 失败: {e}", exc_info=True)
            raise

        # 2.6 创建 Article 对象
        logger.info(f"尝试创建 Article 对象...")
        try:
            article = Article(
                source_id=source_id,
                title=item.get("title", "").strip()[:500],
                url=url,
                published_at=published_at,
                content_text=item.get("content_text", ""),
                content_len=len(item.get("content_text", "") or ""),
                canonical_url=item.get("canonical_url") or url,
                dedup_key=item.get("dedup_key"),
                simhash=item.get("simhash"),
                processing_status=ProcessingStatus.RAW,
            )
            logger.info(f"  ✓ Article 对象创建成功")
            logger.info(f"    - article.source_id = {article.source_id}")
            logger.info(f"    - article.title = {article.title[:50]}")
        except Exception as e:
            logger.error(f"  ✗ 创建 Article 失败: {e}", exc_info=True)
            logger.error(f"  参数:")
            logger.error(f"    - source_id: {source_id}")
            logger.error(f"    - title: {item.get('title', '')[:50]}")
            logger.error(f"    - url: {url[:80] if url else None}")
            raise

        # 2.7 数据库操作
        logger.info(f"尝试写入数据库...")
        try:
            logger.info(f"  - 执行 db.add(article)...")
            db.add(article)
            logger.info(f"  - 执行 db.flush()...")
            db.flush()  # 获取 article.id
            logger.info(f"  ✓ Article 写入成功, ID={article.id}")

            queue_item = ExtractionQueue(
                article_id=article.id,
                status=QueueStatus.QUEUED,
                priority=0,
                attempts=0,
            )
            db.add(queue_item)
            logger.info(f"  ✓ ExtractionQueue 创建成功")

            db.commit()
            logger.info(f"  ✓ 提交成功")

            saved_count += 1
            queued_count += 1
            existing_urls.add(url)

        except IntegrityError as exc:
            logger.warning(f"  ⚠️ 写入失败（可能重复）: {exc}")
            db.rollback()
        except Exception as exc:
            logger.error(f"  ✗ 写入异常: {exc}", exc_info=True)
            db.rollback()

    logger.info(f"\n" + "=" * 80)
    logger.info(f"存储完成: saved={saved_count}, queued={queued_count}")
    logger.info(f"=" * 80)

    return saved_count, queued_count


def main():
    """主测试流程"""
    logger.info("🔍 调试 _store_articles 函数\n")

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

        # 采集
        crawler = RSSCrawler(
            source_id=source.id,
            source_name=source.name,
            source_url=source.url,
            parser=source.parser
        )
        since = get_local_now() - timedelta(hours=24)
        items = crawler.fetch(since=since)

        logger.info(f"采集到 {len(items)} 篇文章")

        if not items:
            logger.warning("无文章，退出")
            return

        # 规范化
        from collections.abc import Mapping
        normalized: List[Dict] = []
        for raw in items:
            if isinstance(raw, Mapping):
                item = dict(raw)
                item.setdefault("source_id", source.id)
                item.setdefault("source_name", source.name)
                canonical_url = item.get("canonical_url") or item.get("url")
                if canonical_url:
                    item["canonical_url"] = canonical_url
                normalized.append(item)

        logger.info(f"规范化后: {len(normalized)} 篇")

        # 去重
        existing_urls = {
            url for (url,) in db.query(Article.url).filter(Article.url.isnot(None))
        }
        existing_hashes = [
            simhash for (simhash,) in db.query(Article.simhash).filter(Article.simhash.isnot(None))
        ]

        deduplicator = Deduplicator()
        items = deduplicator.deduplicate(normalized, existing_urls=existing_urls, existing_hashes=existing_hashes)

        logger.info(f"去重后: {len(items)} 篇")

        if not items:
            logger.warning("去重后无文章，退出")
            return

        # 准备存储
        for item in items:
            if "dedup_key" not in item:
                item["dedup_key"] = deduplicator.generate_dedup_key(item)

        # 调试存储
        saved, queued = debug_store_articles(db, items, source, existing_urls)

        logger.info(f"\n✅ 测试完成: saved={saved}, queued={queued}")

    except Exception as e:
        logger.error(f"\n❌ 测试失败: {e}")
        logger.error(f"错误类型: {type(e)}")
        logger.error(f"错误参数: {e.args}")

        # 打印完整堆栈
        import traceback
        logger.error(f"完整堆栈:\n{traceback.format_exc()}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
