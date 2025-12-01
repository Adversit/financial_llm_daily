#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
重置失败文章状态脚本

将指定日期内状态为 failed 的文章重置为 raw (待处理)状态

用法:
    python scripts/reset_failed_articles.py --date 2025-11-30
    python scripts/reset_failed_articles.py --date 2025-11-30 --dry-run  # 只查看不修改
"""

import argparse
from datetime import datetime, timedelta
from loguru import logger
from sqlalchemy import and_, or_

from src.db.session import SessionLocal
from src.models.article import Article, ProcessingStatus


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


def reset_failed_articles(date_str: str, dry_run: bool = False):
    """
    重置指定日期的失败文章

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
        # 1. published_at 或 fetched_at 在指定日期范围内
        # 2. processing_status = 'failed'
        query = session.query(Article).filter(
            and_(
                or_(
                    and_(Article.published_at >= start_time, Article.published_at < end_time),
                    and_(Article.fetched_at >= start_time, Article.fetched_at < end_time)
                ),
                Article.processing_status == ProcessingStatus.FAILED
            )
        )

        failed_articles = query.all()

        if not failed_articles:
            logger.info("✅ 没有找到状态为 failed 的文章")
            return

        logger.info(f"找到 {len(failed_articles)} 篇状态为 failed 的文章:")
        print("\n" + "=" * 80)
        for i, article in enumerate(failed_articles, 1):
            print(f"{i}. [ID:{article.id}] {article.title[:60]}")
            print(f"   URL: {article.url}")
            print(f"   发布时间: {article.published_at}")
            print(f"   采集时间: {article.fetched_at}")
            print(f"   当前状态: {article.processing_status}")
        print("=" * 80 + "\n")

        if dry_run:
            logger.info("🔍 预览模式: 不执行修改操作")
            logger.info(f"如需修改,请去掉 --dry-run 参数重新执行")
            return

        # 确认修改
        logger.warning(f"即将修改 {len(failed_articles)} 篇文章的状态: failed -> raw")

        # 执行修改
        for article in failed_articles:
            article.processing_status = ProcessingStatus.RAW

        session.commit()

        logger.success(f"✅ 成功修改 {len(failed_articles)} 篇文章的状态为 raw (待处理)")
        logger.info(f"接下来可以运行: python -m src.cli.run_once --step extract --date {date_str}")

    except Exception as e:
        session.rollback()
        logger.error(f"❌ 操作失败: {e}", exc_info=True)
        raise
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(description="重置失败文章状态")
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

    reset_failed_articles(args.date, args.dry_run)


if __name__ == "__main__":
    main()
