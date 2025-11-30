"""
报告任务模块

用于生成日报报告。
"""

import json
from datetime import date, datetime, timedelta

from loguru import logger
from sqlalchemy.orm import Session

from src.composer.builder import (
    build_attachment,
    build_email_body,
    build_metadata,
    generate_section_reports,
)
from src.composer.scorer import (
    filter_items,
    get_sections_statistics,
    section_and_sort,
    select_topn,
)
from src.config.settings import settings
from src.db.session import get_db
from src.models.report import Report
from src.tasks.celery_app import celery_app
from src.utils.time_utils import get_local_now, get_local_now_naive


def _build_report_core_logic(report_date_str: str = None) -> dict:
    """
    报告构建核心逻辑（可独立测试）

    Args:
        report_date_str: 报告日期字符串 (YYYY-MM-DD)，None 表示今天

    Returns:
        任务结果字典
    """
    db: Session = next(get_db())

    try:
        # 解析日期
        if report_date_str:
            report_date = datetime.strptime(report_date_str, "%Y-%m-%d").date()
        else:
            report_date = date.today()

        logger.info(f"开始构建报告: {report_date}")

        # 记录开始时间
        start_time = get_local_now()

        # 1. 过滤抽取项
        logger.info("步骤 1/6: 过滤抽取项")
        items = filter_items(db, report_date)

        if not items:
            logger.warning(f"没有找到 {report_date} 的抽取项，生成空报告")
            # 仍然生成报告，但内容为空
            sections = {}
            sections_topn = {}
            overview = "今日暂无重要金融情报。"
        else:
            # 2. 分区排序
            logger.info(f"步骤 2/6: 分区排序 ({len(items)} 条)")
            sections = section_and_sort(items)

            # 3. 选取 TopN
            logger.info(f"步骤 3/6: 选取 TopN (N={settings.REPORT_TOPN})")
            sections_topn = select_topn(sections, settings.REPORT_TOPN)

            # 4. 生成分区报告（可选，LLM）
            logger.info("步骤 4/6: 生成分区报告")
            section_reports = generate_section_reports(sections)  # 使用全量数据

        # 5. 生成 HTML
        logger.info("步骤 5/6: 生成 HTML")
        html_body = build_email_body(
            report_date=report_date,
            sections_topn=sections_topn,
            section_reports=section_reports if items else {},
        )

        html_attachment = build_attachment(
            report_date=report_date,
            sections_full=sections,
        )

        # 6. 生成元数据
        build_time_ms = int((get_local_now() - start_time).total_seconds() * 1000)
        logger.info(f"步骤 6/6: 生成元数据 (耗时: {build_time_ms}ms)")

        metadata = build_metadata(
            sections=sections,
            topn_sections=sections_topn,
            build_time_ms=build_time_ms,
        )

        # 获取统计信息
        sections_json = get_sections_statistics(sections)

        # 7. 写入数据库
        logger.info("写入报告到数据库")

        # 检查是否已存在当天的报告
        existing_report = (
            db.query(Report)
            .filter(Report.report_date == report_date)
            .first()
        )

        if existing_report:
            logger.info(f"更新已存在的报告: {existing_report.id}")
            existing_report.html_body = html_body
            existing_report.html_attachment = html_attachment
            existing_report.sections_json = json.dumps(sections_json, ensure_ascii=False)
            existing_report.build_meta = json.dumps(metadata, ensure_ascii=False)
            existing_report.build_ms = build_time_ms
            existing_report.updated_at = get_local_now_naive()

            report_id = existing_report.id
        else:
            logger.info("创建新报告")
            report = Report(
                report_date=report_date,
                html_body=html_body,
                html_attachment=html_attachment,
                sections_json=json.dumps(sections_json, ensure_ascii=False),
                build_meta=json.dumps(metadata, ensure_ascii=False),
                build_ms=build_time_ms,
            )
            db.add(report)
            db.flush()
            report_id = report.id

        db.commit()

        # 使用 .get() 安全访问字典，避免 KeyError
        logger.success(
            f"✅ 报告构建完成: report_id={report_id}, "
            f"总数={metadata.get('total_items', 0)}, "
            f"TopN={metadata.get('topn_items', 0)}, "
            f"耗时={build_time_ms}ms"
        )

        return {
            "status": "success",
            "report_id": report_id,
            "report_date": report_date.isoformat(),
            "metadata": metadata,
        }

    except Exception as e:
        logger.error(f"构建报告失败: {e}", exc_info=True)
        db.rollback()

        return {
            "status": "error",
            "error": str(e),
            "report_date": report_date_str or date.today().isoformat(),
        }

    finally:
        db.close()


@celery_app.task(name="src.tasks.report_tasks.build_report_task", bind=True)
def build_report_task(self, report_date_str: str = None) -> dict:
    """
    构建报告任务（Celery 包装器）

    Args:
        report_date_str: 报告日期字符串 (YYYY-MM-DD)，None 表示今天

    Returns:
        任务结果字典
    """
    return _build_report_core_logic(report_date_str)


def _build_report_batch_core_logic(start_date_str: str = None, end_date_str: str = None) -> dict:
    """
    批量构建报告核心逻辑（可独立测试）

    Args:
        start_date_str: 开始日期 (YYYY-MM-DD)
        end_date_str: 结束日期 (YYYY-MM-DD)

    Returns:
        批处理结果
    """
    try:
        # 解析日期
        if start_date_str:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        else:
            start_date = date.today() - timedelta(days=7)

        if end_date_str:
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        else:
            end_date = date.today()

        logger.info(f"开始批量构建报告: {start_date} -> {end_date}")

        # 生成日期列表
        current_date = start_date
        dates = []
        while current_date <= end_date:
            dates.append(current_date.isoformat())
            current_date += timedelta(days=1)

        logger.info(f"共 {len(dates)} 天需要构建")

        # 逐天构建
        results = []
        for date_str in dates:
            try:
                result = build_report_task.apply(args=[date_str])
                results.append(result.get())
                logger.info(f"✅ {date_str} 完成")
            except Exception as e:
                logger.error(f"❌ {date_str} 失败: {e}")
                results.append({
                    "status": "error",
                    "report_date": date_str,
                    "error": str(e)
                })

        success_count = sum(1 for r in results if r.get("status") == "success")

        logger.success(
            f"批量构建完成: {success_count}/{len(dates)} 成功"
        )

        return {
            "status": "success",
            "total": len(dates),
            "success": success_count,
            "failed": len(dates) - success_count,
            "results": results,
        }

    except Exception as e:
        logger.error(f"批量构建报告失败: {e}")
        return {
            "status": "error",
            "error": str(e),
        }


@celery_app.task(name="src.tasks.report_tasks.build_report_batch", bind=True)
def build_report_batch(self, start_date_str: str = None, end_date_str: str = None) -> dict:
    """
    批量构建报告（Celery 包装器）

    Args:
        start_date_str: 开始日期 (YYYY-MM-DD)
        end_date_str: 结束日期 (YYYY-MM-DD)

    Returns:
        批处理结果
    """
    return _build_report_batch_core_logic(start_date_str, end_date_str)
