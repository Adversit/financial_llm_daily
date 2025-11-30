"""
命令行工具 - 手动执行任务

用法:
    python -m src.cli.run_once --step crawl
    python -m src.cli.run_once --step extract --date 2025-11-05
    python -m src.cli.run_once --step compose
    python -m src.cli.run_once --step send
    python -m src.cli.run_once --step all
"""

import sys
from datetime import date, datetime

import click
from loguru import logger

# 配置日志
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO"
)


@click.command()
@click.option(
    "--step",
    type=click.Choice(["crawl", "extract", "compose", "send", "all"]),
    required=True,
    help="执行的步骤",
)
@click.option(
    "--date",
    type=str,
    default=None,
    help="指定日期 YYYY-MM-DD（可选，默认今天）",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="跳过时间窗口等限制（主要用于 send）",
)
def run_once(step: str, date: str, force: bool):
    """
    手动执行单个步骤或完整流程

    示例：
        python -m src.cli.run_once --step crawl
        python -m src.cli.run_once --step extract --date 2025-11-05
        python -m src.cli.run_once --step compose
        python -m src.cli.run_once --step send
        python -m src.cli.run_once --step all
    """
    logger.info(f"开始执行步骤: {step}")

    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
            logger.info(f"指定日期: {target_date}")
        except ValueError:
            logger.error("日期格式错误，应为 YYYY-MM-DD")
            sys.exit(1)
    else:
        target_date = None

    if step == "crawl":
        execute_crawl()
    elif step == "extract":
        execute_extract(target_date)
    elif step == "compose":
        execute_compose(target_date)
    elif step == "send":
        execute_send(target_date, force=force)
    elif step == "all":
        execute_all(target_date, force=force)


def execute_crawl():
    """执行采集任务"""
    logger.info("=" * 50)
    logger.info("执行采集任务")
    logger.info("=" * 50)

    try:
        from src.tasks.orchestrator import run_crawl_only
        from src.tasks.celery_app import celery_app

        # 设置 Celery 为同步模式（用于测试）
        celery_app.conf.task_always_eager = True

        # 调用编排器的采集任务
        result = run_crawl_only.apply()
        result_data = result.get()

        logger.info(f"采集任务结果: {result_data}")

        if result_data.get("status") == "success":
            logger.success(
                f"✅ 采集任务完成: "
                f"信息源={result_data.get('sources_count', 0)}, "
                f"任务数={result_data.get('tasks_count', 0)}"
            )
        elif result_data.get("status") == "skipped":
            logger.warning(f"⚠️ 采集任务跳过: {result_data.get('reason', 'Unknown')}")
        else:
            logger.error(f"❌ 采集任务失败: {result_data.get('error', 'Unknown error')}")

    except Exception as e:
        logger.error(f"执行采集任务失败: {e}", exc_info=True)


def execute_extract(target_date=None):
    """执行抽取任务"""
    logger.info("=" * 50)
    logger.info("执行抽取任务")
    logger.info("=" * 50)

    from src.tasks.extract_tasks import run_extraction_batch

    date_str = target_date.isoformat() if target_date else None

    try:
        result = run_extraction_batch.apply(args=[date_str])
        result_data = result.get()

        logger.info(f"抽取结果: {result_data}")

        if result_data.get("status") == "success":
            logger.success(f"✅ 抽取完成: {result_data.get('total', 0)} 个队列项")
        else:
            logger.error(f"❌ 抽取失败: {result_data.get('error', 'Unknown error')}")

    except Exception as e:
        logger.error(f"执行抽取任务失败: {e}", exc_info=True)


def execute_compose(target_date=None):
    """执行报告生成任务"""
    logger.info("=" * 50)
    logger.info("执行报告生成任务")
    logger.info("=" * 50)

    from src.tasks.report_tasks import build_report_task

    date_str = target_date.isoformat() if target_date else None

    try:
        result = build_report_task.apply(args=[date_str])
        result_data = result.get()

        logger.info(f"报告生成结果: {result_data}")

        if result_data.get("status") == "success":
            metadata = result_data.get("metadata", {})
            logger.success(
                f"✅ 报告生成完成: report_id={result_data.get('report_id')}, "
                f"总数={metadata.get('total_items', 0)}, "
                f"TopN={metadata.get('topn_items', 0)}, "
                f"耗时={metadata.get('build_time_ms', 0)}ms"
            )
        else:
            logger.error(f"❌ 报告生成失败: {result_data.get('error', 'Unknown error')}")

    except Exception as e:
        logger.error(f"执行报告生成任务失败: {e}", exc_info=True)


def execute_send(target_date=None, force: bool = False):
    """执行邮件发送任务"""
    logger.info("=" * 50)
    logger.info("执行邮件发送任务")
    logger.info("=" * 50)

    try:
        from src.tasks.mail_tasks import send_report_task
        from src.tasks.celery_app import celery_app

        # 设置 Celery 为同步模式（用于测试）
        celery_app.conf.task_always_eager = True

        # 解析日期
        date_str = target_date.isoformat() if target_date else date.today().isoformat()
        logger.info(f"发送日期: {date_str}")

        # 调用邮件发送任务
        kwargs = {"force_send": force} if force else {}
        result = send_report_task.apply(args=[date_str], kwargs=kwargs)
        result_data = result.get()

        logger.info(f"邮件发送结果: {result_data}")

        if result_data.get("status") == "success":
            logger.success(
                f"✅ 邮件发送完成: report_id={result_data.get('report_id')}, "
                f"收件人={result_data.get('total_recipients', 0)}, "
                f"批次={result_data.get('total_batches', 0)}, "
                f"成功={result_data.get('success_batches', 0)}, "
                f"失败={result_data.get('failed_batches', 0)}"
            )
        elif result_data.get("status") == "skipped":
            logger.warning(f"⚠️ 邮件发送跳过: {result_data.get('reason', 'Unknown')}")
        else:
            logger.error(f"❌ 邮件发送失败: {result_data.get('error', 'Unknown error')}")

    except Exception as e:
        logger.error(f"执行邮件发送任务失败: {e}", exc_info=True)


def execute_all(target_date=None, force: bool = False):
    """依次执行采集、抽取、生成和发送任务"""
    logger.info("=" * 50)
    logger.info("执行完整流程（顺序执行模块）")
    logger.info("=" * 50)

    try:
        from src.tasks.orchestrator import run_crawl_only
        from src.tasks.extract_tasks import run_extraction_batch
        from src.tasks.report_tasks import build_report_task
        from src.tasks.mail_tasks import send_report_task
        from src.tasks.celery_app import celery_app

        # 将 Celery 切换为同步执行，确保命令顺序运行
        celery_app.conf.task_always_eager = True

        date_str = target_date.isoformat() if target_date else None
        logger.info(f"执行日期: {date_str or '今天'}")

        steps = [
            ("采集任务", run_crawl_only, None, {}),
            ("抽取任务", run_extraction_batch, date_str, {}),
            ("报告生成", build_report_task, date_str, {}),
            ("邮件发送", send_report_task, date_str, {"force_send": force}),
        ]

        for label, task, arg, kwargs in steps:
            logger.info(f"➡️ 开始{label}")

            args = [arg] if arg is not None else []
            try:
                result = task.apply(args=args, kwargs=kwargs)
                result_data = result.get()
            except Exception as exc:
                logger.error(f"❌ {label}执行异常: {exc}", exc_info=True)
                break

            logger.info(f"{label}结果: {result_data}")

            status = result_data.get("status")
            if status == "success":
                logger.success(f"✅ {label}完成")
            elif status == "skipped":
                logger.warning(f"⚠️ {label}跳过: {result_data.get('reason', 'Unknown')}")
            else:
                logger.error(f"❌ {label}失败: {result_data.get('error', 'Unknown error')}")
                break
        else:
            logger.success("🎉 全部步骤顺序执行完成")

    except Exception as e:
        logger.error(f"执行完整流程失败: {e}", exc_info=True)

    logger.info("=" * 50)
    logger.info("完整流程执行结束")
    logger.info("=" * 50)


if __name__ == "__main__":
    run_once()
