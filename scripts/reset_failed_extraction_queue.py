#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
重置失败的抽取队列状态脚本

将指定日期内状态为 failed 的抽取队列项重置为 queued (待处理)状态

用法:
    python scripts/reset_failed_extraction_queue.py --date 2025-11-30
    python scripts/reset_failed_extraction_queue.py --date 2025-11-30 --dry-run  # 只查看不修改
"""

import argparse
from datetime import datetime, timedelta
from loguru import logger
from sqlalchemy import and_, or_

from src.db.session import SessionLocal
from src.models.article import Article
from src.models.extraction import ExtractionQueue, QueueStatus


def parse_date(date_str: str) -> tuple[datetime, datetime]:
    """
    解析日期字符串,返回当天的开始和结束时间

    Args:
        date_str: 日期字符串 (YYYY-MM-DD)

    Returns:
        tuple[datetime, datetime]: (开始时间, 结束时间)
    """
    date = datetime.strptime(date_str, "%Y-%m-%d")
    start_time = date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_time = start_time + timedelta(days=1)
    return start_time, end_time


def reset_failed_queue(date_str: str, dry_run: bool = False):
    """
    重置指定日期的失败抽取队列项

    Args:
        date_str: 日期字符串 (YYYY-MM-DD)
        dry_run: 是否只查看不修改
    """
    start_time, end_time = parse_date(date_str)

    logger.info(f"{'[预览模式] ' if dry_run else ''}处理日期: {date_str}")
    logger.info(f"时间范围: {start_time} ~ {end_time}")

    session = SessionLocal()
    try:
        # 查询条件:
        # 1. 关联 articles 表,筛选 published_at 或 fetched_at 在指定日期范围内
        # 2. extraction_queue.status = 'failed'
        query = session.query(ExtractionQueue).join(
            Article, ExtractionQueue.article_id == Article.id
        ).filter(
            and_(
                or_(
                    and_(Article.published_at >= start_time, Article.published_at < end_time),
                    and_(Article.fetched_at >= start_time, Article.fetched_at < end_time)
                ),
                ExtractionQueue.status == QueueStatus.FAILED
            )
        )

        failed_queues = query.all()

        if not failed_queues:
            logger.info("✅ 没有找到状态为 failed 的抽取队列项")
            return

        logger.info(f"找到 {len(failed_queues)} 个状态为 failed 的抽取队列项:")
        print("\n" + "=" * 80)
        for i, queue in enumerate(failed_queues, 1):
            article = queue.article
            print(f"{i}. [Queue ID:{queue.id}] [Article ID:{queue.article_id}]")
            print(f"   标题: {article.title[:60]}")
            print(f"   URL: {article.url[:80]}")
            print(f"   发布时间: {article.published_at}")
            print(f"   采集时间: {article.fetched_at}")
            print(f"   队列状态: {queue.status}")
            print(f"   尝试次数: {queue.attempts}")
            if queue.last_error:
                print(f"   最后错误: {queue.last_error[:100]}...")
        print("=" * 80 + "\n")

        if dry_run:
            logger.info("🔍 预览模式: 不执行修改操作")
            logger.info(f"如需修改,请去掉 --dry-run 参数重新执行")
            return

        # 确认修改
        logger.warning(f"即将修改 {len(failed_queues)} 个队列项的状态: failed -> queued")

        # 执行修改
        for queue in failed_queues:
            queue.status = QueueStatus.QUEUED
            # 可选: 重置尝试次数和错误信息
            # queue.attempts = 0
            # queue.last_error = None
            # queue.processing_started_at = None
            # queue.processing_finished_at = None

        session.commit()

        logger.success(f"✅ 成功修改 {len(failed_queues)} 个队列项的状态为 queued (待处理)")
        logger.info(f"接下来可以运行: python -m src.cli.run_once --step extract --date {date_str}")

    except Exception as e:
        session.rollback()
        logger.error(f"❌ 操作失败: {e}", exc_info=True)
        raise
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(description="重置失败的抽取队列状态")
    parser.add_argument(
        "--date",
        type=str,
        required=True,
        help="指定日期 (格式: YYYY-MM-DD, 例如: 2025-11-30)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览模式,只查看不修改"
    )

    args = parser.parse_args()

    # 验证日期格式
    try:
        datetime.strptime(args.date, "%Y-%m-%d")
    except ValueError:
        logger.error("❌ 日期格式错误,请使用 YYYY-MM-DD 格式 (例如: 2025-11-30)")
        return

    reset_failed_queue(args.date, args.dry_run)


if __name__ == "__main__":
    main()
