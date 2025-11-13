"""
报告浏览路由
"""
from __future__ import annotations

from datetime import date
from typing import List, Optional

import bleach
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.models.report import Report
from src.models.user import User
from src.web.deps import get_current_user

router = APIRouter(prefix="/reports", tags=["Reports"])

ALLOWED_TAGS = list(
    set(bleach.sanitizer.ALLOWED_TAGS).union(
        {
            "table", "thead", "tbody", "tr", "th", "td", "h1", "h2", "h3", "h4",
            "section", "article", "span", "div", "style", "html", "head", "body",
            "meta", "title", "link", "p", "br", "strong", "em", "ul", "ol", "li"
        }
    )
)
ALLOWED_ATTRIBUTES = {
    "*": ["style", "class", "id"],
    "a": ["href", "title", "target", "rel"],
    "img": ["src", "alt", "title"],
    "meta": ["charset", "name", "content"],
    "div": ["class", "style", "id"],
}


def _clean_html(html: str) -> str:
    return bleach.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES, strip=True)


@router.get("", response_class=HTMLResponse)
async def report_list(
    request: Request,
    current_user: User = Depends(get_current_user),
    report_date: Optional[date] = Query(default=None, description="指定日期"),
    db: Session = Depends(get_db),
):
    """报告列表页面"""
    query = db.query(Report).order_by(Report.report_date.desc())
    if report_date:
        query = query.filter(Report.report_date == report_date)
    reports: List[Report] = query.limit(30).all()

    return request.app.state.templates.TemplateResponse(
        "reports/list.html",
        {
            "request": request,
            "reports": reports,
            "current_user": current_user,
            "selected_date": report_date.isoformat() if report_date else "",
        },
    )


@router.get("/{report_date}", response_class=HTMLResponse)
async def report_detail(
    report_date: date,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """报告详情页面"""
    report = db.query(Report).filter(Report.report_date == report_date).first()
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到指定日期的报告")

    sanitized_html = _clean_html(report.html_body)

    return request.app.state.templates.TemplateResponse(
        "reports/detail.html",
        {
            "request": request,
            "report": report,
            "report_html": sanitized_html,
            "current_user": current_user,
        },
    )


@router.post("/trigger-all-tasks")
async def trigger_all_tasks_user(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """用户端手动触发所有任务（采集→抽取→成稿→发送）"""
    from src.tasks.orchestrator import run_daily_report
    from datetime import datetime

    try:
        # 触发完整的日报生成流程
        result = run_daily_report.apply_async()

        return {
            "status": "success",
            "message": "所有任务已成功触发",
            "task_id": result.id
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"任务触发失败: {str(e)}"
        }
