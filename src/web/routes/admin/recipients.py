"""
管理员 - 收件人与白名单管理
"""
from __future__ import annotations

from typing import List, Optional

from email_validator import EmailNotValidError, validate_email
from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.models.delivery import RecipientType, ReportRecipient
from src.models.system import AdminAuditLog
from src.models.user import User
from src.utils.time_utils import get_local_now_naive
from src.web.deps import require_admin

router = APIRouter(prefix="/recipients", tags=["Admin-Recipients"])


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
async def admin_recipients_page(
    request: Request,
    recipient_type: Optional[str] = Query(default=None, description="recipient | whitelist"),
    success: Optional[str] = Query(default=None, description="success message"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """收件人管理页面"""

    query = db.query(ReportRecipient).order_by(ReportRecipient.created_at.desc())

    # 筛选类型
    if recipient_type:
        try:
            type_enum = RecipientType(recipient_type)
            query = query.filter(ReportRecipient.type == type_enum)
        except ValueError:
            pass

    recipients: List[ReportRecipient] = query.all()

    return _templates(request).TemplateResponse(
        "admin/recipients.html",
        {
            "request": request,
            "current_user": current_user,
            "recipients": recipients,
            "filter_type": recipient_type,
            "page_title": "收件人管理",
            "success_message": success
        }
    )


@router.post("/create")
async def create_recipient(
    request: Request,
    email: str = Form(...),
    display_name: Optional[str] = Form(default=None),
    recipient_type: str = Form(..., alias="type"),
    enabled: bool = Form(default=True),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """创建收件人"""

    # 验证邮箱格式
    try:
        validated = validate_email(email, check_deliverability=False)
        normalized_email = validated.normalized
    except EmailNotValidError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid email: {e}")

    # 验证类型
    try:
        type_enum = RecipientType(recipient_type)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid type: {recipient_type}")

    # 检查该邮箱的该类型是否已存在
    existing = db.query(ReportRecipient).filter(
        ReportRecipient.email == normalized_email,
        ReportRecipient.type == type_enum
    ).first()
    if existing:
        type_label = "收件人" if type_enum == RecipientType.RECIPIENT else "白名单"
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"该邮箱已作为{type_label}存在")

    # 创建记录
    recipient = ReportRecipient(
        email=normalized_email,
        display_name=display_name.strip() if display_name else None,
        type=type_enum,
        enabled=enabled
    )
    db.add(recipient)
    db.flush()

    # 审计日志
    _log_audit(
        db, current_user, "create_recipient", "recipient", recipient.id,
        before={},
        after={
            "email": recipient.email,
            "display_name": recipient.display_name,
            "type": recipient.type.value,
            "enabled": recipient.enabled
        },
        request=request
    )

    db.commit()

    # 添加成功消息
    type_label = "收件人" if type_enum == RecipientType.RECIPIENT else "白名单"
    from urllib.parse import quote
    success_msg = quote(f"✓ 成功添加{type_label}: {normalized_email}")
    return RedirectResponse(url=f"/admin/recipients?success={success_msg}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{recipient_id}/update")
async def update_recipient(
    recipient_id: int,
    request: Request,
    display_name: Optional[str] = Form(default=None),
    enabled: bool = Form(...),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """更新收件人"""

    recipient = db.query(ReportRecipient).filter(ReportRecipient.id == recipient_id).first()
    if not recipient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipient not found")

    before = {
        "display_name": recipient.display_name,
        "enabled": recipient.enabled
    }

    recipient.display_name = display_name.strip() if display_name else None
    recipient.enabled = enabled

    after = {
        "display_name": recipient.display_name,
        "enabled": recipient.enabled
    }

    db.add(recipient)
    _log_audit(db, current_user, "update_recipient", "recipient", recipient_id, before, after, request)
    db.commit()

    return RedirectResponse(url="/admin/recipients", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{recipient_id}/delete")
async def delete_recipient(
    recipient_id: int,
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """删除收件人"""

    recipient = db.query(ReportRecipient).filter(ReportRecipient.id == recipient_id).first()
    if not recipient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipient not found")

    before = {
        "email": recipient.email,
        "display_name": recipient.display_name,
        "type": recipient.type.value,
        "enabled": recipient.enabled
    }

    db.delete(recipient)
    _log_audit(db, current_user, "delete_recipient", "recipient", recipient_id, before, {}, request)
    db.commit()

    return RedirectResponse(url="/admin/recipients", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{recipient_id}/toggle")
async def toggle_recipient(
    recipient_id: int,
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """快速切换启用状态"""

    recipient = db.query(ReportRecipient).filter(ReportRecipient.id == recipient_id).first()
    if not recipient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipient not found")

    before = {"enabled": recipient.enabled}
    recipient.enabled = not recipient.enabled
    after = {"enabled": recipient.enabled}

    db.add(recipient)
    _log_audit(db, current_user, "toggle_recipient", "recipient", recipient_id, before, after, request)
    db.commit()

    return RedirectResponse(url="/admin/recipients", status_code=status.HTTP_303_SEE_OTHER)
