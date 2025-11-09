"""
用户偏好路由
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Form, Path, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.models.user import PreferenceScope, User, UserPreference
from src.web.deps import get_current_user

router = APIRouter(prefix="/preferences", tags=["Preferences"])
MAX_PROMPT_LEN = 2000
MAX_PREFS_PER_USER = 5


def _templates(request: Request):
    return request.app.state.templates


def _load_prefs(db: Session, user: User):
    return (
        db.query(UserPreference)
        .filter(UserPreference.user_email == user.email)
        .order_by(UserPreference.created_at.desc())
        .all()
    )


@router.get("", response_class=HTMLResponse)
async def preferences_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """展示偏好列表"""
    prefs = _load_prefs(db, current_user)
    return _templates(request).TemplateResponse(
        "preferences/index.html",
        {
            "request": request,
            "preferences": prefs,
            "current_user": current_user,
            "error": None,
            "max_templates": MAX_PREFS_PER_USER,
        },
    )


@router.post("", response_class=HTMLResponse)
async def save_preference(
    request: Request,
    name: str = Form(...),
    scope: str = Form(...),
    prompt_text: str = Form(...),
    is_default: Optional[str] = Form(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建或更新偏好"""
    prefs = _load_prefs(db, current_user)

    try:
        scope_enum = PreferenceScope(scope)
    except ValueError:
        return _templates(request).TemplateResponse(
            "preferences/index.html",
            {
                "request": request,
                "preferences": prefs,
                "current_user": current_user,
                "error": "非法的作用范围",
                "max_templates": MAX_PREFS_PER_USER,
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    if len(prompt_text.strip()) == 0:
        return _templates(request).TemplateResponse(
            "preferences/index.html",
            {
                "request": request,
                "preferences": prefs,
                "current_user": current_user,
                "error": "提示词内容不能为空",
                "max_templates": MAX_PREFS_PER_USER,
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    if len(prompt_text) > MAX_PROMPT_LEN:
        return _templates(request).TemplateResponse(
            "preferences/index.html",
            {
                "request": request,
                "preferences": prefs,
                "current_user": current_user,
                "error": f"提示词长度超限（最多 {MAX_PROMPT_LEN} 字符）",
                "max_templates": MAX_PREFS_PER_USER,
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    existing = (
        db.query(UserPreference)
        .filter(UserPreference.user_email == current_user.email, UserPreference.name == name.strip())
        .first()
    )

    should_set_default = is_default is not None

    if existing:
        existing.scope = scope_enum
        existing.prompt_text = prompt_text.strip()
        existing.is_default = should_set_default
        target_pref = existing
    else:
        if len(prefs) >= MAX_PREFS_PER_USER:
            return _templates(request).TemplateResponse(
                "preferences/index.html",
                {
                    "request": request,
                    "preferences": prefs,
                    "current_user": current_user,
                    "error": f"最多创建 {MAX_PREFS_PER_USER} 条模板",
                    "max_templates": MAX_PREFS_PER_USER,
                },
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        target_pref = UserPreference(
            user_email=current_user.email,
            name=name.strip(),
            scope=scope_enum,
            prompt_text=prompt_text.strip(),
            is_default=should_set_default,
        )
        db.add(target_pref)
        db.flush()

    if should_set_default:
        (
            db.query(UserPreference)
            .filter(
                UserPreference.user_email == current_user.email,
                UserPreference.id != target_pref.id,
            )
            .update({"is_default": False}, synchronize_session=False)
        )

    db.commit()

    return RedirectResponse(url="/preferences", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{pref_id}/delete")
async def delete_preference(
    pref_id: int = Path(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除偏好"""
    pref = (
        db.query(UserPreference)
        .filter(UserPreference.id == pref_id, UserPreference.user_email == current_user.email)
        .first()
    )
    if pref:
        db.delete(pref)
        db.commit()
    return RedirectResponse(url="/preferences", status_code=status.HTTP_303_SEE_OTHER)
