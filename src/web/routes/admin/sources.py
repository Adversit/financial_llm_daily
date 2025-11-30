"""
管理员 - 信息源管理
"""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.models.source import Source
from src.models.system import AdminAuditLog
from src.models.user import User
from src.utils.time_utils import get_local_now_naive
from src.web.deps import require_admin

router = APIRouter(prefix="/sources", tags=["Admin-Sources"])


def _templates(request: Request):
    return request.app.state.templates


def _log_audit(db: Session, admin: User, action: str, resource_type: str, resource_id: int, before: dict, after: dict, request: Request):
    """记录审计日志"""
    log = AdminAuditLog(
        admin_email=admin.email,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        before_json=before,
        after_json=after,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        created_at=get_local_now_naive()
    )
    db.add(log)


@router.get("", response_class=HTMLResponse)
async def admin_sources_page(
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """信息源管理页面"""
    sources: List[Source] = db.query(Source).order_by(Source.created_at.desc()).all()

    return _templates(request).TemplateResponse(
        "admin/sources.html",
        {
            "request": request,
            "current_user": current_user,
            "sources": sources,
            "page_title": "信息源管理"
        }
    )


@router.post("/{source_id}/update")
async def update_source(
    source_id: int,
    request: Request,
    enabled: bool = Form(...),
    concurrency: int = Form(...),
    timeout_sec: int = Form(...),
    parser: str = Form(default=None),
    region_hint: str = Form(...),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """更新信息源配置"""

    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")

    # 记录修改前数据
    before = {
        "enabled": source.enabled,
        "concurrency": source.concurrency,
        "timeout_sec": source.timeout_sec,
        "parser": source.parser,
        "region_hint": source.region_hint.value if source.region_hint else None
    }

    # 更新字段
    source.enabled = enabled
    source.concurrency = max(1, min(concurrency, 50))  # 限制范围 1-50
    source.timeout_sec = max(5, min(timeout_sec, 300))  # 限制范围 5-300
    source.parser = parser if parser and parser.strip() else None

    # 更新region_hint (需要验证枚举值)
    from src.models.source import RegionHint
    try:
        source.region_hint = RegionHint(region_hint)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid region_hint: {region_hint}")

    db.add(source)

    # 记录修改后数据
    after = {
        "enabled": source.enabled,
        "concurrency": source.concurrency,
        "timeout_sec": source.timeout_sec,
        "parser": source.parser,
        "region_hint": source.region_hint.value if source.region_hint else None
    }

    # 写入审计日志
    _log_audit(db, current_user, "update_source", "source", source_id, before, after, request)

    db.commit()

    return RedirectResponse(url="/admin/sources", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{source_id}/toggle")
async def toggle_source(
    source_id: int,
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """快速切换信息源启用状态"""

    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")

    before = {"enabled": source.enabled}
    source.enabled = not source.enabled
    after = {"enabled": source.enabled}

    db.add(source)

    _log_audit(db, current_user, "toggle_source", "source", source_id, before, after, request)

    db.commit()

    return RedirectResponse(url="/admin/sources", status_code=status.HTTP_303_SEE_OTHER)
