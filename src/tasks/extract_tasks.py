"""
抽取任务模块
"""

import asyncio
from datetime import datetime
from typing import Optional

from loguru import logger
from sqlalchemy.orm import Session

from src.config.settings import settings
from src.db.session import get_db
from src.models.article import Article, ProcessingStatus
from src.models.delivery import ProviderUsage
from src.models.extraction import (
    ExtractionItem,
    ExtractionQueue,
    Layer,
    QueueStatus,
    Region,
)
from src.nlp.extractor import extract_article
from src.nlp.merger import filter_low_quality_items
from src.tasks.celery_app import celery_app
from src.utils.time_utils import get_local_now_naive


def log_provider_usage(
    db: Session,
    provider: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    cost: float = 0.0,
) -> None:
    """
    记录 Provider 使用情况

    Args:
        db: 数据库会话
        provider: Provider 名称
        model: 模型名称
        prompt_tokens: Prompt tokens
        completion_tokens: Completion tokens
        cost: 费用（元）
    """
    try:
        usage = ProviderUsage(
            provider_name=provider,
            model_name=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            cost=cost,
        )
        db.add(usage)
        db.commit()
        logger.debug(
            f"记录 Provider 使用: {provider}/{model}, "
            f"tokens={prompt_tokens + completion_tokens}, cost={cost}"
        )
    except Exception as e:
        logger.error(f"记录 Provider 使用失败: {e}")
        db.rollback()


@celery_app.task(name="src.tasks.extract_tasks.extract_article_task", bind=True)
def extract_article_task(self, article_id: int) -> dict:
    """
    抽取单篇文章

    Args:
        article_id: 文章ID

    Returns:
        任务结果字典
    """
    db: Session = next(get_db())

    try:
        logger.info(f"开始处理文章抽取任务: article_id={article_id}")

        # 1. 检查并更新队列状态
        queue_item = (
            db.query(ExtractionQueue)
            .filter(ExtractionQueue.article_id == article_id)
            .first()
        )

        if not queue_item:
            logger.error(f"队列项不存在: article_id={article_id}")
            return {"status": "error", "message": "队列项不存在"}

        # 更新为运行中
        queue_item.status = QueueStatus.RUNNING
        queue_item.attempts += 1
        queue_item.processing_started_at = get_local_now_naive()
        db.commit()

        # 2. 执行抽取
        result = asyncio.run(extract_article(article_id, db))

        # 3. 处理结果
        if result.status == "success" or result.status == "partial":
            # 过滤低质量项
            filtered_items = filter_low_quality_items(
                result.items,
                min_confidence=settings.CONFIDENCE_THRESHOLD,
                min_fact_length=30,
            )

            logger.info(
                f"抽取完成: {len(result.items)} 条 -> "
                f"过滤后 {len(filtered_items)} 条"
            )

            # 4. 写入 extraction_items
            for item in filtered_items:
                try:
                    # 映射枚举值
                    region_map = {
                        "国内": Region.DOMESTIC,
                        "国外": Region.FOREIGN,
                        "未知": Region.UNKNOWN,
                    }
                    layer_map = {
                        "金融政策监管": Layer.FINANCIAL_POLICY,
                        "金融经济": Layer.FINANCIAL_ECONOMY,
                        "金融大模型技术": Layer.FINTECH_AI,
                        "金融科技应用": Layer.FINTECH,
                        # 兼容旧值
                        "政治": Layer.FINANCIAL_POLICY,
                        "经济": Layer.FINANCIAL_ECONOMY,
                        "金融科技": Layer.FINTECH,
                        "未知": Layer.UNKNOWN,
                    }

                    extraction_item = ExtractionItem(
                        article_id=article_id,
                        fact=item.get("fact", ""),
                        opinion=item.get("opinion", ""),
                        region=region_map.get(item.get("region", "未知"), Region.UNKNOWN),
                        layer=layer_map.get(item.get("layer", "未知"), Layer.UNKNOWN),
                        evidence_span=item.get("evidence_span", ""),
                        confidence=item.get("confidence", 0.0),
                        finance_relevance=item.get("finance_relevance", 1.0),
                    )
                    db.add(extraction_item)

                except Exception as e:
                    logger.error(f"写入 extraction_item 失败: {e}")
                    continue

            # 5. 更新队列状态为完成
            queue_item.status = QueueStatus.DONE
            queue_item.processing_finished_at = get_local_now_naive()
            queue_item.last_error = None

            # 6. 更新文章处理状态
            article = db.query(Article).filter(Article.id == article_id).first()
            if article:
                article.processing_status = ProcessingStatus.DONE

            db.commit()

            # 7. 记录 Provider 使用情况
            usage = result.metadata.get("usage", {})
            if usage:
                # 估算费用（需要根据实际 Provider 价格计算）
                # DeepSeek: ¥0.001/1K tokens (示例)
                total_tokens = usage.get("total_tokens", 0)
                cost = (total_tokens / 1000) * 0.001

                log_provider_usage(
                    db=db,
                    provider="deepseek",  # 实际应从 metadata 获取
                    model=settings.PROVIDER_DEEPSEEK_MODEL,
                    prompt_tokens=usage.get("prompt_tokens", 0),
                    completion_tokens=usage.get("completion_tokens", 0),
                    cost=cost,
                )

            logger.success(
                f"✅ 文章 {article_id} 抽取成功，"
                f"写入 {len(filtered_items)} 条结果"
            )

            return {
                "status": "success",
                "article_id": article_id,
                "items_count": len(filtered_items),
                "metadata": result.metadata,
            }

        else:
            # 抽取失败
            queue_item.status = QueueStatus.FAILED
            queue_item.processing_finished_at = get_local_now_naive()
            queue_item.last_error = result.error

            # 更新文章状态
            article = db.query(Article).filter(Article.id == article_id).first()
            if article:
                article.processing_status = ProcessingStatus.FAILED

            db.commit()

            logger.error(f"❌ 文章 {article_id} 抽取失败: {result.error}")

            return {
                "status": "failed",
                "article_id": article_id,
                "error": result.error,
            }

    except Exception as e:
        logger.error(f"处理文章 {article_id} 时发生异常: {e}")

        # 更新失败状态
        try:
            queue_item = (
                db.query(ExtractionQueue)
                .filter(ExtractionQueue.article_id == article_id)
                .first()
            )
            if queue_item:
                queue_item.status = QueueStatus.FAILED
                queue_item.processing_finished_at = get_local_now_naive()
                queue_item.last_error = str(e)

            article = db.query(Article).filter(Article.id == article_id).first()
            if article:
                article.processing_status = ProcessingStatus.FAILED

            db.commit()
        except Exception as commit_error:
            logger.error(f"更新失败状态时发生错误: {commit_error}")
            db.rollback()

        return {
            "status": "error",
            "article_id": article_id,
            "error": str(e),
        }

    finally:
        db.close()


@celery_app.task(name="src.tasks.extract_tasks.run_extraction_batch")
def run_extraction_batch(date_filter: Optional[str] = None) -> dict:
    """
    批量处理抽取队列

    Args:
        date_filter: 日期过滤（YYYY-MM-DD），None 表示处理所有待处理项

    Returns:
        批处理结果
    """
    db: Session = next(get_db())

    try:
        logger.info("开始批量抽取任务")

        # 查询待处理的队列项
        query = db.query(ExtractionQueue).filter(
            ExtractionQueue.status == QueueStatus.QUEUED
        )

        # 如果指定了日期，过滤
        if date_filter:
            from datetime import datetime

            target_date = datetime.strptime(date_filter, "%Y-%m-%d").date()
            query = query.join(Article).filter(
                Article.created_at >= target_date,
                Article.created_at < datetime.combine(
                    target_date, datetime.max.time()
                ),
            )

        # 按优先级排序
        queue_items = query.order_by(ExtractionQueue.priority.desc()).all()

        total = len(queue_items)
        logger.info(f"找到 {total} 个待处理队列项")

        if total == 0:
            return {
                "status": "success",
                "message": "没有待处理的队列项",
                "total": 0,
            }

        # 决定是串行还是并行处理
        if settings.LLM_ALLOW_PARALLEL_ARTICLE_PROCESSING:
            logger.info("并行处理模式")
            # 并行处理（使用 Celery group）
            from celery import group

            job = group(
                extract_article_task.s(item.article_id) for item in queue_items
            )
            result = job.apply_async()
            result.get()  # 等待所有任务完成

        else:
            logger.info("串行处理模式")
            # 串行处理
            for item in queue_items:
                try:
                    extract_article_task.apply(args=[item.article_id])
                except Exception as e:
                    logger.error(f"处理队列项 {item.id} 失败: {e}")
                    continue

        logger.success(f"✅ 批量抽取任务完成，处理了 {total} 个队列项")

        return {
            "status": "success",
            "total": total,
        }

    except Exception as e:
        logger.error(f"批量抽取任务失败: {e}")
        return {
            "status": "error",
            "error": str(e),
        }

    finally:
        db.close()
