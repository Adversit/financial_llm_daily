"""
静态资源与下载路由
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.models.report import Report
from src.models.user import User
from src.web.deps import get_current_user

router = APIRouter(prefix="/assets", tags=["Assets"])


@router.get("/attachment/{report_date}.html")
async def download_report_attachment(
    report_date: date,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """下载报告附件（HTML格式）"""

    # 查询报告
    report = db.query(Report).filter(Report.report_date == report_date).first()

    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report not found for date {report_date}"
        )

    if not report.html_attachment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report attachment not available for date {report_date}"
        )

    # 返回附件
    filename = f"daily-report-{report_date.isoformat()}.html"

    return Response(
        content=report.html_attachment,
        media_type="text/html",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "public, max-age=3600"
        }
    )
