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
        {"table", "thead", "tbody", "tr", "th", "td", "h1", "h2", "h3", "h4", "section", "article", "span"}
    )
)
ALLOWED_ATTRIBUTES = {
    "*": ["style", "class"],
    "a": ["href", "title", "target", "rel"],
    "img": ["src", "alt", "title"],
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
