"""
重新运行指定文章的抽取任务

用法:
    python scripts/retry_article.py <article_id>
    python scripts/retry_article.py 472
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.models.article import Article, ProcessingStatus
from src.models.extraction import ExtractionQueue, QueueStatus
from src.tasks.celery_app import celery_app
from src.tasks.extract_tasks import extract_article_task


def retry_article(article_id: int):
    """
    重新运行指定文章的抽取任务

    Args:
        article_id: 文章ID
    """
    logger.info("=" * 60)
    logger.info(f"开始重新运行文章 {article_id} 的抽取任务")
    logger.info("=" * 60)

    db: Session = next(get_db())

    try:
        # 1. 检查文章是否存在
        article = db.query(Article).filter(Article.id == article_id).first()
        if not article:
            logger.error(f"❌ 文章不存在: article_id={article_id}")
            return False

        logger.info(f"文章标题: {article.title}")
        logger.info(f"当前状态: {article.processing_status.value}")
        logger.info(f"内容长度: {len(article.content_text or '')} 字符")

        # 2. 检查队列项
        queue_item = (
            db.query(ExtractionQueue)
            .filter(ExtractionQueue.article_id == article_id)
            .first()
        )

        if not queue_item:
            logger.warning(f"⚠️ 队列项不存在，创建新的队列项")
            queue_item = ExtractionQueue(
                article_id=article_id,
                status=QueueStatus.QUEUED,
                priority=100,  # 高优先级
                attempts=0,
            )
            db.add(queue_item)
            db.commit()
        else:
            logger.info(f"队列状态: {queue_item.status.value}")
            logger.info(f"已尝试次数: {queue_item.attempts}")
            logger.info(f"上次错误: {queue_item.last_error or '无'}")

        # 3. 重置状态
        logger.info("重置队列状态为 QUEUED...")
        queue_item.status = QueueStatus.QUEUED
        queue_item.last_error = None
        queue_item.processing_started_at = None
        queue_item.processing_finished_at = None

        article.processing_status = ProcessingStatus.QUEUED

        db.commit()

        # 4. 配置 Celery 同步执行模式（用于测试）
        celery_app.conf.task_always_eager = True

        # 5. 调用抽取任务
        logger.info("开始执行抽取任务...")
        logger.info("")

        result = extract_article_task.apply(args=[article_id])
        result_data = result.get()

        logger.info("")
        logger.info("=" * 60)
        logger.info("执行结果")
        logger.info("=" * 60)
        logger.info(f"状态: {result_data.get('status')}")

        if result_data.get("status") == "success":
            items_count = result_data.get("items_count", 0)
            metadata = result_data.get("metadata", {})

            logger.success(f"✅ 文章 {article_id} 抽取成功!")
            logger.info(f"抽取条目数: {items_count}")
            logger.info(f"使用 Provider: {metadata.get('provider', 'unknown')}")
            logger.info(f"使用 Model: {metadata.get('model', 'unknown')}")

            usage = metadata.get('usage', {})
            if usage:
                logger.info(
                    f"Token 使用: "
                    f"prompt={usage.get('prompt_tokens', 0)}, "
                    f"completion={usage.get('completion_tokens', 0)}, "
                    f"total={usage.get('total_tokens', 0)}"
                )

            return True

        else:
            error = result_data.get("error", "Unknown error")
            logger.error(f"❌ 文章 {article_id} 抽取失败: {error}")
            return False

    except Exception as e:
        logger.error(f"执行过程中发生异常: {e}", exc_info=True)
        return False

    finally:
        db.close()


def main():
    """主函数"""
    if len(sys.argv) != 2:
        logger.error("用法: python scripts/retry_article.py <article_id>")
        logger.error("示例: python scripts/retry_article.py 472")
        sys.exit(1)

    try:
        article_id = int(sys.argv[1])
    except ValueError:
        logger.error(f"❌ 无效的文章ID: {sys.argv[1]}")
        sys.exit(1)

    success = retry_article(article_id)

    if success:
        logger.success("🎉 任务执行成功!")
        sys.exit(0)
    else:
        logger.error("❌ 任务执行失败!")
        sys.exit(1)


if __name__ == "__main__":
    main()
