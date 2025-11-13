"""
采集任务模块

负责调度模块 A 的采集器，将文章落库并加入抽取队列。
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.crawlers.base import BaseCrawler
from src.crawlers.deduplicator import Deduplicator
from src.crawlers.rss_crawler import RSSCrawler
from src.crawlers.static_crawler import StaticCrawler
from src.crawlers.dynamic_crawler import DynamicCrawler
from src.crawlers.browser_pool import BrowserPool
from src.db.session import get_db
from src.models.article import Article, ProcessingStatus
from src.models.extraction import ExtractionQueue, QueueStatus
from src.models.source import Source, SourceType
from src.tasks.celery_app import celery_app
from src.utils.time_utils import get_local_now, to_local_naive
from src.config.settings import settings


# 全局浏览器池实例（单例模式）
_browser_pool: Optional[BrowserPool] = None


def get_browser_pool() -> BrowserPool:
    """获取或创建浏览器池单例"""
    import asyncio

    global _browser_pool
    if _browser_pool is None:
        logger.info("初始化浏览器池...")
        _browser_pool = BrowserPool(
            max_contexts=getattr(settings, 'PLAYWRIGHT_MAX_BROWSERS', 5),
            headless=getattr(settings, 'PLAYWRIGHT_HEADLESS', True)
        )
        # 启动浏览器
        try:
            asyncio.run(_browser_pool.start())
            logger.success("浏览器池启动成功")
        except Exception as e:
            logger.error(f"浏览器池启动失败: {e}")
            _browser_pool = None
            raise
    return _browser_pool


def _get_db_session() -> Session:
    """获取数据库会话。"""
    return next(get_db())


def _load_source(db: Session, source_id: int) -> Optional[Source]:
    """加载信息源，找不到返回 None。"""
    return (
        db.query(Source)
        .filter(Source.id == source_id)
        .first()
    )


def _build_crawler(source: Source) -> Optional[BaseCrawler]:
    """根据信息源类型构建对应的采集器。"""
    parser = getattr(source, "parser", None)
    parser_config = getattr(source, "parser_config", None) or {}

    if source.type == SourceType.RSS:
        return RSSCrawler(source.id, source.name, source.url, parser)
    if source.type == SourceType.STATIC:
        return StaticCrawler(source.id, source.name, source.url, parser)
    if source.type == SourceType.DYNAMIC:
        # 获取浏览器池
        browser_pool = get_browser_pool()
        return DynamicCrawler(
            source.id,
            source.name,
            source.url,
            browser_pool,
            parser=parser,
            parser_config=parser_config
        )

    logger.warning(f"暂不支持的信息源类型: {source.type}")
    return None


def _load_existing_references(db: Session) -> Tuple[set, List[int]]:
    """加载已有文章的 URL 和 SimHash，用于去重。"""
    existing_urls = {
        url for (url,) in db.query(Article.url).filter(Article.url.isnot(None))
    }
    existing_hashes = [
        simhash for (simhash,) in db.query(Article.simhash).filter(Article.simhash.isnot(None))
    ]
    return existing_urls, existing_hashes


def _prepare_items_for_storage(items: List[Dict], deduplicator: Deduplicator) -> List[Dict]:
    """使用去重器生成去重键等辅助字段。"""
    for item in items:
        if "dedup_key" not in item:
            item["dedup_key"] = deduplicator.generate_dedup_key(item)
    return items


def _normalize_crawl_items(raw_items: List[Any], source: Source) -> List[Dict]:
    """统一采集结果的结构，确保包含 source 元数据等必需字段。"""
    normalized: List[Dict] = []

    for raw in raw_items:
        item: Optional[Dict[str, Any]] = None

        if isinstance(raw, Mapping):
            item = dict(raw)
        elif hasattr(raw, "__dict__"):
            # dataclass 或普通对象
            item = {k: v for k, v in vars(raw).items() if not k.startswith("_")}

        if item is None:
            logger.warning(f"未知采集项类型，已跳过: type={type(raw)}")
            continue

        # 补齐来源信息
        item.setdefault("source_id", source.id)
        item.setdefault("source_name", source.name)

        # canonical_url 至少回落到 url，便于去重
        canonical_url = item.get("canonical_url") or item.get("url")
        if canonical_url:
            item["canonical_url"] = canonical_url

        normalized.append(item)

    return normalized


def _store_articles(
    db: Session,
    items: List[Dict],
    source: Source,
    existing_urls: set,
) -> Tuple[int, int]:
    """
    将文章写入数据库，并加入抽取队列。

    Returns:
        (新增文章数量, 加入抽取队列数量)
    """
    saved_count = 0
    queued_count = 0

    normalized_items: List[Dict] = []

    for raw in items:
        if isinstance(raw, Mapping):
            normalized_items.append(dict(raw))
        else:
            logger.warning(f"未知采集项类型，已跳过: type={type(raw)}")

    for item in normalized_items:
        source_id = item.get("source_id", source.id)
        if "source_id" not in item:
            logger.warning(
                f"采集结果缺少 source_id，使用当前源 {source.id}",
            )

        source_name = item.get("source_name", source.name)

        url = item.get("url")
        if not url:
            continue

        if url in existing_urls:
            logger.debug(f"URL 已存在，跳过: {url}")
            continue

        published_at = item.get("published_at")
        if published_at:
            published_at = to_local_naive(published_at)

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

        try:
            db.add(article)
            db.flush()  # 获取 article.id

            queue_item = ExtractionQueue(
                article_id=article.id,
                status=QueueStatus.QUEUED,
                priority=0,
                attempts=0,
            )
            db.add(queue_item)

            db.commit()

            saved_count += 1
            queued_count += 1
            existing_urls.add(url)

        except IntegrityError as exc:
            logger.warning(f"写入文章失败（可能重复）: {url} - {exc}")
            db.rollback()
        except Exception as exc:
            logger.error(f"写入文章时发生异常: {url} - {exc}", exc_info=True)
            db.rollback()

    return saved_count, queued_count


def _run_crawl(source_id: int, expected_type: Optional[SourceType] = None) -> Dict:
    """通用采集执行逻辑。"""
    db = _get_db_session()

    try:
        source = _load_source(db, source_id)
        if not source:
            logger.error(f"信息源不存在: source_id={source_id}")
            return {"status": "error", "reason": "source_not_found", "source_id": source_id}

        if expected_type and source.type != expected_type:
            logger.warning(f"信息源类型不匹配: source_id={source_id}, expected={expected_type}, actual={source.type}")
            return {"status": "skipped", "reason": "type_mismatch", "source_id": source_id}

        if not source.enabled:
            logger.info(f"信息源已禁用，跳过: source_id={source_id}")
            return {"status": "skipped", "reason": "source_disabled", "source_id": source_id}

        crawler = _build_crawler(source)
        if not crawler:
            return {"status": "skipped", "reason": "unsupported_source_type", "source_id": source_id}

        since = get_local_now() - timedelta(hours=24)
        items = crawler.fetch(since=since)
        fetched = len(items)

        if not items:
            logger.info(f"未获取到文章: source_id={source_id}")
            return {
                "status": "success",
                "source_id": source_id,
                "source_type": source.type.value,
                "fetched": 0,
                "saved": 0,
                "queued": 0,
            }

        items = _normalize_crawl_items(items, source)
        if not items:
            logger.info(f"采集结果均被过滤或无法识别，跳过: source_id={source_id}")
            return {
                "status": "success",
                "source_id": source_id,
                "source_type": source.type.value,
                "fetched": fetched,
                "after_normalize": 0,
                "saved": 0,
                "queued": 0,
            }

        deduplicator = Deduplicator()
        existing_urls, existing_hashes = _load_existing_references(db)

        items = deduplicator.deduplicate(items, existing_urls=existing_urls, existing_hashes=existing_hashes)
        items = _prepare_items_for_storage(items, deduplicator)

        try:
            saved, queued = _store_articles(db, items, source, existing_urls)
        except KeyError as exc:
            sample_info = []
            for raw in items[:5]:
                if hasattr(raw, "keys"):
                    keys = list(raw.keys())
                elif isinstance(raw, dict):
                    keys = list(raw.keys())
                else:
                    keys = f"(type={type(raw)})"
                sample_info.append(keys)

            logger.error(
                f"存储文章时缺少键: {exc}. 样例字段: {sample_info}",
                exc_info=True
            )
            raise

        logger.success(
            f"采集完成: source_id={source_id}, 原始={fetched}, 去重后={len(items)}, 新增={saved}, 入队={queued}"
        )

        return {
            "status": "success",
            "source_id": source_id,
            "source_type": source.type.value,
            "fetched": fetched,
            "after_dedup": len(items),
            "saved": saved,
            "queued": queued,
        }

    except Exception as exc:
        logger.error(f"采集任务失败: source_id={source_id}, error={exc}", exc_info=True)
        return {"status": "error", "source_id": source_id, "error": str(exc)}
    finally:
        db.close()


@celery_app.task(name="src.tasks.crawl_tasks.crawl_rss_task")
def crawl_rss_task(source_id: int) -> Dict:
    """采集 RSS 信息源。"""
    return _run_crawl(source_id, expected_type=SourceType.RSS)


@celery_app.task(name="src.tasks.crawl_tasks.crawl_static_task")
def crawl_static_task(source_id: int) -> Dict:
    """采集静态网页信息源。"""
    return _run_crawl(source_id, expected_type=SourceType.STATIC)


@celery_app.task(name="src.tasks.crawl_tasks.crawl_dynamic_task")
def crawl_dynamic_task(source_id: int) -> Dict:
    """采集动态网页信息源（Playwright）。"""
    return _run_crawl(source_id, expected_type=SourceType.DYNAMIC)


@celery_app.task(name="src.tasks.crawl_tasks.cleanup_browser_pool")
def cleanup_browser_pool() -> Dict:
    """
    清理浏览器池任务（定时任务，用于释放资源）
    可配置在每天凌晨执行一次
    """
    import asyncio

    global _browser_pool

    try:
        if _browser_pool is not None:
            logger.info("开始清理浏览器池...")
            asyncio.run(_browser_pool.close())
            _browser_pool = None
            logger.success("浏览器池已清理")
            return {"status": "success", "message": "Browser pool cleaned"}
        else:
            logger.info("浏览器池未初始化，无需清理")
            return {"status": "success", "message": "Browser pool not initialized"}
    except Exception as e:
        logger.error(f"清理浏览器池失败: {e}")
        return {"status": "error", "message": str(e)}
