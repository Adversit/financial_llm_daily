"""
邮件任务模块

用于发送日报邮件。
"""

import asyncio
from datetime import date, datetime

from loguru import logger
from sqlalchemy.orm import Session

from src.config.settings import settings
from src.db.session import get_db
from src.mailer.batcher import (
    RateLimiter,
    batch_recipients,
    filter_valid_recipients,
    remove_duplicates,
)
from src.mailer.retry_handler import handle_send_failure, send_with_retry
from src.mailer.smtp_client import SMTPClient
from src.models.delivery import DeliveryLog, ReportRecipient
from src.models.report import Report
from src.tasks.celery_app import celery_app
from src.utils.time_utils import get_local_now, get_local_now_naive, to_local_naive


def _send_report_core_logic(report_date_str: str = None, force_send: bool = False) -> dict:
    """
    发送报告邮件核心逻辑（可独立测试）

    Args:
        report_date_str: 报告日期字符串 (YYYY-MM-DD)，None 表示今天

    Returns:
        发送结果字典
    """
    db: Session = next(get_db())

    try:
        # 解析日期
        if report_date_str:
            report_date = datetime.strptime(report_date_str, "%Y-%m-%d").date()
        else:
            report_date = date.today()

        logger.info(f"开始发送报告邮件: {report_date}")

        # 串行执行模式：无需时间窗口检查，任务完成即可发送
        if force_send:
            logger.info("⏩ 手动发送模式")

        # 1. 读取报告
        report = (
            db.query(Report)
            .filter(Report.report_date == report_date)
            .first()
        )

        if not report:
            logger.error(f"❌ 报告不存在: {report_date}")
            return {
                "status": "error",
                "error": "report_not_found",
                "report_date": report_date.isoformat(),
            }

        # 3. 读取收件人（启用的）
        recipients = (
            db.query(ReportRecipient.email)
            .filter(
                ReportRecipient.type == "recipient",
                ReportRecipient.enabled == True
            )
            .all()
        )

        recipient_emails = [email for (email,) in recipients]

        if not recipient_emails:
            logger.warning("⚠️ 没有启用的收件人，跳过发送")
            return {
                "status": "skipped",
                "reason": "no_recipients",
                "report_date": report_date.isoformat(),
            }

        # 4. 验证和去重
        recipient_emails = filter_valid_recipients(recipient_emails)
        recipient_emails = remove_duplicates(recipient_emails)

        logger.info(f"有效收件人数量: {len(recipient_emails)}")

        # 5. 组装邮件内容
        subject = f"金融情报日报 - {report_date.strftime('%Y年%m月%d日')}"
        html_body = report.html_body
        attachment_filename = f"daily-report-{report_date.isoformat()}.html"
        attachment_content = report.html_attachment.encode('utf-8')

        # 6. 分批
        batches = batch_recipients(recipient_emails)
        logger.info(f"邮件分为 {len(batches)} 批")

        # 7. 异步发送
        results = asyncio.run(
            _send_batches_async(
                db=db,
                batches=batches,
                subject=subject,
                html_body=html_body,
                attachment_filename=attachment_filename,
                attachment_content=attachment_content,
                report_id=report.id,
                report_date=report_date
            )
        )

        # 8. 统计结果
        success_count = sum(1 for r in results if r['status'] == 'ok')
        failed_count = len(results) - success_count

        logger.success(
            f"✅ 邮件发送完成: {success_count}/{len(results)} 成功, "
            f"{failed_count} 失败"
        )

        return {
            "status": "success",
            "report_date": report_date.isoformat(),
            "report_id": report.id,
            "total_recipients": len(recipient_emails),
            "total_batches": len(batches),
            "success_batches": success_count,
            "failed_batches": failed_count,
            "results": results,
        }

    except Exception as e:
        logger.error(f"发送报告邮件失败: {e}", exc_info=True)
        db.rollback()

        return {
            "status": "error",
            "error": str(e),
            "report_date": report_date_str or date.today().isoformat(),
        }

    finally:
        db.close()


async def _send_batches_async(
    db: Session,
    batches: list,
    subject: str,
    html_body: str,
    attachment_filename: str,
    attachment_content: bytes,
    report_id: int,
    report_date: date
) -> list:
    """
    异步发送所有批次

    Args:
        db: 数据库会话
        batches: 批次列表
        subject: 邮件主题
        html_body: 邮件正文
        attachment_filename: 附件文件名
        attachment_content: 附件内容
        report_id: 报告ID
        report_date: 报告日期

    Returns:
        发送结果列表
    """
    # 创建 SMTP 客户端
    smtp_client = SMTPClient()

    # 创建频率限制器
    rate_limiter = RateLimiter()

    # 发送结果
    results = []

    for i, batch in enumerate(batches, start=1):
        logger.info(f"发送批次 {i}/{len(batches)}: To={batch['to']}, BCC={len(batch['bcc'])} 个")

        # 等待（频率限制）
        await rate_limiter.throttle()

        # 组装邮件数据
        email_data = {
            "to": batch['to'],
            "bcc": batch['bcc'],
            "subject": subject,
            "html_body": html_body,
            "attachments": [(attachment_filename, attachment_content)]
        }

        # 发送（带重试）
        result = await send_with_retry(smtp_client, email_data, max_retries=2)

        # 记录发送日志
        _log_delivery(
            db=db,
            report_id=report_id,
            batch_num=i,
            batch_data=batch,
            result=result
        )

        # 处理失败
        if result['status'] == 'failed':
            await handle_send_failure(db, batch, result.get('error', 'Unknown'))

        results.append(result)

    return results


def _log_delivery(
    db: Session,
    report_id: int,
    batch_num: int,
    batch_data: dict,
    result: dict
):
    """
    记录发送日志

    Args:
        db: 数据库会话
        report_id: 报告ID
        report_date: 报告日期
        batch_num: 批次编号
        batch_data: 批次数据（to, bcc）
        result: 发送结果
    """
    try:
        recipients_snapshot = {
            "to": batch_data.get("to", []),
            "bcc": batch_data.get("bcc", []),
        }

        sent_at = None
        sent_at_str = result.get("sent_at")
        if sent_at_str:
            try:
                sent_at = datetime.fromisoformat(sent_at_str)
                sent_at = to_local_naive(sent_at)
            except ValueError:
                sent_at = None
        if result.get("status") == "ok" and sent_at is None:
            sent_at = get_local_now_naive()

        log = DeliveryLog(
            report_id=report_id,
            batch_no=batch_num,
            recipients_snapshot=recipients_snapshot,
            status=result.get("status", "failed"),
            message_id=result.get("message_id"),
            error_message=result.get("error"),
            sent_at=sent_at or get_local_now_naive(),
        )

        db.add(log)
        db.commit()

    except Exception as e:
        logger.error(f"记录发送日志失败: {e}")
        db.rollback()


def check_time_window(
    start: str = None,
    end: str = None,
    current_time: datetime = None
) -> bool:
    """
    检查是否在发送时间窗口内

    Args:
        start: 开始时间（HH:MM 格式）
        end: 结束时间（HH:MM 格式）
        current_time: 当前时间（用于测试，默认使用系统时间）

    Returns:
        是否在窗口内
    """
    start = start or settings.MAIL_WINDOW_START
    end = end or settings.MAIL_WINDOW_END

    # 解析时间
    start_time = datetime.strptime(start, "%H:%M").time()
    end_time = datetime.strptime(end, "%H:%M").time()

    # 获取当前时间
    current_time = current_time or get_local_now()
    current = current_time.time()

    # 判断是否在窗口内
    if start_time <= end_time:
        # 正常情况：06:00 - 08:00
        return start_time <= current <= end_time
    else:
        # 跨午夜情况：23:00 - 01:00
        return current >= start_time or current <= end_time


@celery_app.task(name="src.tasks.mail_tasks.send_report_task", bind=True)
def send_report_task(self, report_date_str: str = None, force_send: bool = False) -> dict:
    """
    发送报告邮件任务（Celery 包装器）

    Args:
        report_date_str: 报告日期字符串 (YYYY-MM-DD)，None 表示今天

    Returns:
        发送结果字典
    """
    return _send_report_core_logic(report_date_str, force_send=force_send)
