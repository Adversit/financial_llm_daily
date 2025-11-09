"""
调试所有信息源的采集流程

直接调用 crawl_tasks 的实际代码，逐个测试所有启用的源
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from src.db.session import get_db
from src.models.source import Source, SourceType
from src.utils.logger import logger


def test_all_enabled_sources():
    """测试所有启用的信息源"""
    logger.info("=" * 80)
    logger.info("测试所有启用的信息源采集")
    logger.info("=" * 80)

    db: Session = next(get_db())

    try:
        # 获取所有启用的源
        sources = db.query(Source).filter(Source.enabled == True).all()

        logger.info(f"\n找到 {len(sources)} 个启用的信息源\n")

        for idx, source in enumerate(sources, 1):
            logger.info("=" * 80)
            logger.info(f"[{idx}/{len(sources)}] 测试源: {source.name}")
            logger.info(f"  - ID: {source.id}")
            logger.info(f"  - 类型: {source.type.value}")
            logger.info(f"  - URL: {source.url}")
            logger.info("=" * 80)

            # 根据类型调用对应的任务
            try:
                if source.type == SourceType.RSS:
                    from src.tasks.crawl_tasks import crawl_rss_task
                    result = crawl_rss_task(source.id)
                elif source.type == SourceType.STATIC:
                    from src.tasks.crawl_tasks import crawl_static_task
                    result = crawl_static_task(source.id)
                else:
                    logger.warning(f"不支持的类型: {source.type.value}")
                    continue

                # 打印结果
                logger.info(f"\n✅ 采集结果:")
                logger.info(f"  - 状态: {result.get('status')}")
                logger.info(f"  - 原始数量: {result.get('fetched', 0)}")
                logger.info(f"  - 去重后: {result.get('after_dedup', 0)}")
                logger.info(f"  - 新增: {result.get('saved', 0)}")
                logger.info(f"  - 入队: {result.get('queued', 0)}")

                if result.get('status') == 'error':
                    logger.error(f"  - 错误: {result.get('error', 'unknown')}")
                    logger.error(f"  - 原因: {result.get('reason', 'unknown')}")

                    # 这是关键：找到第一个失败的源就停止
                    logger.error(f"\n❌ 在源 [{source.id}] {source.name} 处失败，停止测试")
                    return source.id

            except Exception as e:
                logger.error(f"\n❌ 采集异常: {e}", exc_info=True)
                logger.error(f"失败的源: ID={source.id}, Name={source.name}")
                return source.id

            logger.info("")  # 空行分隔

        logger.info("=" * 80)
        logger.info("✅ 所有源测试完成，未发现错误")
        logger.info("=" * 80)
        return None

    finally:
        db.close()


def test_specific_source(source_id: int):
    """测试特定源的详细信息"""
    logger.info("\n" + "=" * 80)
    logger.info(f"详细测试源 ID: {source_id}")
    logger.info("=" * 80)

    db: Session = next(get_db())

    try:
        source = db.query(Source).filter(Source.id == source_id).first()

        if not source:
            logger.error(f"源不存在: ID={source_id}")
            return

        logger.info(f"源信息:")
        logger.info(f"  - ID: {source.id}")
        logger.info(f"  - 名称: {source.name}")
        logger.info(f"  - 类型: {source.type.value}")
        logger.info(f"  - URL: {source.url}")
        logger.info(f"  - 启用: {source.enabled}")
        logger.info(f"  - 并发: {source.concurrency}")
        logger.info(f"  - 超时: {source.timeout_sec}s")
        logger.info(f"  - 解析器: {source.parser}")
        logger.info(f"  - 区域: {source.region_hint.value if source.region_hint else 'None'}")

        # 创建采集器并测试
        from datetime import timedelta
        from src.utils.time_utils import get_local_now

        if source.type == SourceType.RSS:
            from src.crawlers.rss_crawler import RSSCrawler
            crawler = RSSCrawler(
                source_id=source.id,
                source_name=source.name,
                source_url=source.url,
                parser=source.parser
            )
        elif source.type == SourceType.STATIC:
            from src.crawlers.static_crawler import StaticCrawler
            crawler = StaticCrawler(
                source_id=source.id,
                source_name=source.name,
                source_url=source.url,
                parser=source.parser
            )
        else:
            logger.error(f"不支持的类型: {source.type.value}")
            return

        logger.info(f"\n开始采集...")
        since = get_local_now() - timedelta(hours=24)
        items = crawler.fetch(since=since)

        logger.info(f"\n采集结果: {len(items)} 篇文章")

        # 检查前3篇
        for i, item in enumerate(items[:3], 1):
            logger.info(f"\n--- 文章 {i} ---")
            logger.info(f"类型: {type(item)}")

            if isinstance(item, dict):
                logger.info(f"字段: {list(item.keys())}")
                logger.info(f"source_id: {item.get('source_id', 'NOT_FOUND')}")
                logger.info(f"source_name: {item.get('source_name', 'NOT_FOUND')}")
                logger.info(f"title: {item.get('title', 'N/A')[:80]}")
                logger.info(f"url: {item.get('url', 'N/A')[:80]}")
                logger.info(f"content_text 长度: {len(item.get('content_text', '') or '')}")
            else:
                logger.warning(f"非字典类型: {type(item)}")
                if hasattr(item, '__dict__'):
                    logger.info(f"属性: {list(vars(item).keys())}")

    finally:
        db.close()


def main():
    """主测试流程"""
    logger.info("🔍 测试所有启用源的采集流程\n")

    # 测试所有源，找到第一个失败的
    failed_source_id = test_all_enabled_sources()

    if failed_source_id:
        # 如果有失败的源，详细测试它
        logger.info(f"\n{'=' * 80}")
        logger.info(f"发现失败的源 ID: {failed_source_id}")
        logger.info(f"进行详细测试...")
        logger.info(f"{'=' * 80}\n")
        test_specific_source(failed_source_id)
    else:
        logger.info("\n✅ 所有源测试通过，未发现问题")


if __name__ == "__main__":
    main()
