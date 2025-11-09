"""
认证与登录路由
"""
from __future__ import annotations

from datetime import timedelta

from email_validator import EmailNotValidError, validate_email
from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from loguru import logger
from sqlalchemy.orm import Session

from src.config.settings import settings
from src.db.session import get_db
from src.models.delivery import RecipientType, ReportRecipient
from src.models.user import User, UserRole
from src.utils.time_utils import get_local_now_naive
from src.web import auth as otp_service
from src.web.security import create_access_token, verify_password

router = APIRouter(tags=["Auth"])
DEFAULT_LOGIN_DOMAIN = "system.local"


def _templates(request: Request):
    return request.app.state.templates


def _normalize_email(email: str) -> str:
    """使用 email-validator 归一化邮箱；若缺少 @ 则补全默认域名"""
    email = (email or "").strip()
    if "@" not in email:
        email = f"{email}@{DEFAULT_LOGIN_DOMAIN}"

    # 对于 @system 这样的本地域名，跳过严格验证
    if email.endswith("@system"):
        # 简单验证格式: 用户名@system
        parts = email.split("@")
        if len(parts) == 2 and parts[0]:
            return email.lower()
        raise EmailNotValidError("邮箱格式错误")

    # 其他邮箱使用标准验证
    info = validate_email(email, check_deliverability=False)
    return info.normalized


def _safe_next_url(next_url: str | None) -> str:
    if not next_url:
        return "/reports"
    if not next_url.startswith("/"):
        return "/reports"
    return next_url


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, next: str | None = None, error: str | None = None):
    """登录页面"""
    return _templates(request).TemplateResponse(
        "auth/login.html",
        {"request": request, "next": next, "error": error},
    )


@router.post("/auth/otp/request")
async def request_otp(email: str = Form(...), db: Session = Depends(get_db)):
    """请求 OTP 验证码"""
    try:
        normalized_email = _normalize_email(email)
    except EmailNotValidError:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"success": False, "error": "邮箱格式错误"})

    recipient = (
        db.query(ReportRecipient)
        .filter(
            ReportRecipient.email == normalized_email,
            ReportRecipient.type == RecipientType.WHITELIST,
            ReportRecipient.enabled.is_(True),
        )
        .first()
    )

    if recipient is None:
        # 防止枚举：返回统一提示
        return {"success": True, "message": "若邮箱在白名单内，将在 1 分钟内收到验证码"}

    if not otp_service.check_resend_interval(normalized_email):
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"success": False, "error": "请求过于频繁，请稍后再试"},
        )

    otp = otp_service.generate_otp()
    otp_service.store_otp(normalized_email, otp)

    sent = await otp_service.send_otp_email(normalized_email, otp)
    if not sent:
        return JSONResponse(status_code=500, content={"success": False, "error": "验证码发送失败，请稍后重试"})

    return {"success": True, "message": "验证码已发送，请查收邮箱"}


@router.post("/auth/otp/verify", response_class=HTMLResponse)
async def verify_login(
    request: Request,
    email: str = Form(...),
    otp: str = Form(""),
    password: str | None = Form(default=None),
    next: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    """校验验证码或管理员密码，登录系统"""
    try:
        normalized_email = _normalize_email(email)
    except EmailNotValidError:
        return _templates(request).TemplateResponse(
            "auth/login.html",
            {
                "request": request,
                "error": "邮箱格式错误",
                "next": next,
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    user = db.query(User).filter(User.email == normalized_email).first()
    login_success = False
    method = "otp"

    # 管理员密码登录优先
    if password and user and verify_password(password, user.hashed_password):
        login_success = True
        method = "password"
        otp_service.reset_otp_attempts(normalized_email)

    if not login_success:
        if not otp:
            return _templates(request).TemplateResponse(
                "auth/login.html",
                {"request": request, "error": "验证码不能为空", "next": next},
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        if not otp_service.check_otp_attempts(normalized_email):
            return _templates(request).TemplateResponse(
                "auth/login.html",
                {
                    "request": request,
                    "error": "尝试次数过多，请稍后再试",
                    "next": next,
                },
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        if not otp_service.verify_otp(normalized_email, otp):
            otp_service.increment_otp_attempts(normalized_email)
            return _templates(request).TemplateResponse(
                "auth/login.html",
                {
                    "request": request,
                    "error": "验证码错误或已过期",
                    "next": next,
                },
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        otp_service.reset_otp_attempts(normalized_email)
        login_success = True
        method = "otp"

    if not login_success:
        return _templates(request).TemplateResponse(
            "auth/login.html",
            {"request": request, "error": "登录失败，请重试", "next": next},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    if user is None:
        user = User(email=normalized_email, role=UserRole.USER, is_active=True)
        db.add(user)
        db.commit()
        db.refresh(user)

    user.last_login_at = get_local_now_naive()
    db.add(user)
    db.commit()

    logger.info("User {} logged in via {}", normalized_email, method)

    token = create_access_token({"sub": user.email, "role": user.role.value}, expires_delta=timedelta(days=settings.JWT_EXPIRE_DAYS))
    response = RedirectResponse(url=_safe_next_url(next), status_code=status.HTTP_302_FOUND)
    secure_cookie = settings.ENV not in {"development", "test"}
    response.set_cookie(
        "access_token",
        token,
        max_age=settings.JWT_EXPIRE_DAYS * 24 * 3600,
        httponly=True,
        samesite="lax",
        secure=secure_cookie,
    )
    return response


@router.post("/logout")
async def logout():
    """退出登录"""
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("access_token")
    return response
