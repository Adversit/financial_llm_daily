"""
任务编排器

协调整个日报生成流程：采集 → 抽取 → 成稿 → 发送
"""

from datetime import date, datetime
from typing import Optional

from celery import chain, group
from loguru import logger
from sqlalchemy.orm import Session

from src.config.settings import settings
from src.db.session import get_db
from src.models.source import Source
from src.tasks.celery_app import celery_app
from src.utils.logger import log_task_start, log_task_end
from src.utils.time_utils import get_local_now


def _run_daily_report_core_logic(report_date_str: Optional[str] = None) -> dict:
    """
    每日报告生成核心逻辑（可独立测试）

    完整流程：
    1. 采集所有启用的信息源
    2. 批量抽取采集到的文章
    3. 生成报告
    4. 发送邮件

    Args:
        report_date_str: 报告日期 (YYYY-MM-DD)，None 表示今天

    Returns:
        执行结果字典
    """
    db: Session = next(get_db())

    try:
        # 解析日期
        if report_date_str:
            report_date = datetime.strptime(report_date_str, "%Y-%m-%d").date()
        else:
            report_date = date.today()

        log_task_start("daily_report", date=report_date.isoformat())
        start_time = get_local_now()

        # 1. 获取所有启用的信息源
        sources = (
            db.query(Source)
            .filter(Source.enabled == True)
            .all()
        )

        if not sources:
            logger.warning("⚠️ 没有启用的信息源")
            return {
                "status": "skipped",
                "reason": "no_enabled_sources",
                "report_date": report_date.isoformat()
            }

        logger.info(f"找到 {len(sources)} 个启用的信息源")

        # 2. 导入任务（延迟导入，避免循环依赖）
        from src.tasks.crawl_tasks import crawl_rss_task, crawl_static_task
        from src.tasks.extract_tasks import run_extraction_batch
        from src.tasks.report_tasks import build_report_task
        from src.tasks.mail_tasks import send_report_task

        # 3. 创建采集任务列表
        crawl_tasks = []
        for source in sources:
            if source.type == "rss":
                crawl_tasks.append(crawl_rss_task.si(source.id))
            elif source.type == "static":
                crawl_tasks.append(crawl_static_task.si(source.id))
            else:
                logger.warning(f"未知的信息源类型: {source.type} (source_id={source.id})")

        if not crawl_tasks:
            logger.warning("⚠️ 没有可执行的采集任务")
            return {
                "status": "skipped",
                "reason": "no_crawl_tasks",
                "report_date": report_date.isoformat()
            }

        logger.info(f"创建 {len(crawl_tasks)} 个采集任务")

        # 4. 构建任务链
        # 采集（并发） → 抽取 → 成稿 → 发送（串行）
        workflow = chain(
            # 步骤 1: 并发采集所有源
            group(*crawl_tasks),

            # 步骤 2: 批量抽取
            run_extraction_batch.si(report_date.isoformat()),

            # 步骤 3: 生成报告
            build_report_task.si(report_date.isoformat()),

            # 步骤 4: 发送邮件
            send_report_task.si(report_date.isoformat())
        )

        # 5. 异步执行工作流
        result = workflow.apply_async()

        # 计算耗时
        duration_ms = (get_local_now() - start_time).total_seconds() * 1000

        log_task_end(
            "daily_report",
            success=True,
            duration_ms=duration_ms,
            sources=len(sources),
            tasks=len(crawl_tasks),
            workflow_id=result.id
        )

        return {
            "status": "success",
            "report_date": report_date.isoformat(),
            "sources_count": len(sources),
            "tasks_count": len(crawl_tasks),
            "workflow_id": result.id,
            "message": "工作流已提交执行"
        }

    except Exception as e:
        logger.error(f"每日报告编排失败: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "report_date": report_date_str or date.today().isoformat()
        }

    finally:
        db.close()


@celery_app.task(name="src.tasks.orchestrator.run_daily_report", bind=True)
def run_daily_report(self, report_date_str: Optional[str] = None) -> dict:
    """
    每日报告生成任务（Celery 包装器）

    这是定时任务的入口，由 Celery Beat 每天早上 6:00 触发。

    Args:
        report_date_str: 报告日期 (YYYY-MM-DD)，None 表示今天

    Returns:
        执行结果字典
    """
    return _run_daily_report_core_logic(report_date_str)


def _run_crawl_only_core_logic() -> dict:
    """
    仅执行采集任务核心逻辑

    Returns:
        执行结果字典
    """
    db: Session = next(get_db())

    try:
        log_task_start("crawl_only")

        # 获取所有启用的信息源
        sources = (
            db.query(Source)
            .filter(Source.enabled == True)
            .all()
        )

        if not sources:
            logger.warning("⚠️ 没有启用的信息源")
            return {
                "status": "skipped",
                "reason": "no_enabled_sources"
            }

        # 导入任务
        from src.tasks.crawl_tasks import crawl_rss_task, crawl_static_task

        # 创建采集任务列表
        crawl_tasks = []
        for source in sources:
            if source.type == "rss":
                crawl_tasks.append(crawl_rss_task.si(source.id))
            elif source.type == "static":
                crawl_tasks.append(crawl_static_task.si(source.id))

        if not crawl_tasks:
            return {
                "status": "skipped",
                "reason": "no_crawl_tasks"
            }

        # 并发执行所有采集任务
        job = group(*crawl_tasks)
        result = job.apply_async()

        log_task_end("crawl_only", success=True, tasks=len(crawl_tasks), group_id=result.id)

        return {
            "status": "success",
            "sources_count": len(sources),
            "tasks_count": len(crawl_tasks),
            "group_id": result.id,
            "message": "采集任务已提交执行"
        }

    except Exception as e:
        logger.error(f"采集任务编排失败: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e)
        }

    finally:
        db.close()


@celery_app.task(name="src.tasks.orchestrator.run_crawl_only", bind=True)
def run_crawl_only(self) -> dict:
    """
    仅执行采集任务（Celery 包装器）

    Returns:
        执行结果字典
    """
    return _run_crawl_only_core_logic()


def _run_extraction_only_core_logic(report_date_str: Optional[str] = None) -> dict:
    """
    仅执行抽取任务核心逻辑

    Args:
        report_date_str: 报告日期 (YYYY-MM-DD)

    Returns:
        执行结果字典
    """
    try:
        if report_date_str:
            report_date = datetime.strptime(report_date_str, "%Y-%m-%d").date()
        else:
            report_date = date.today()

        log_task_start("extraction_only", date=report_date.isoformat())

        from src.tasks.extract_tasks import run_extraction_batch

        result = run_extraction_batch.apply_async(args=[report_date.isoformat()])

        log_task_end("extraction_only", success=True, task_id=result.id)

        return {
            "status": "success",
            "report_date": report_date.isoformat(),
            "task_id": result.id,
            "message": "抽取任务已提交执行"
        }

    except Exception as e:
        logger.error(f"抽取任务编排失败: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e)
        }


@celery_app.task(name="src.tasks.orchestrator.run_extraction_only", bind=True)
def run_extraction_only(self, report_date_str: Optional[str] = None) -> dict:
    """
    仅执行抽取任务（Celery 包装器）

    Args:
        report_date_str: 报告日期 (YYYY-MM-DD)

    Returns:
        执行结果字典
    """
    return _run_extraction_only_core_logic(report_date_str)
