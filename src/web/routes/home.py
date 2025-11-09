"""
首页与通用路由
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse

from src.models.user import User
from src.web.deps import get_current_user_optional

router = APIRouter()


@router.get("/", include_in_schema=False)
async def root(current_user: User | None = Depends(get_current_user_optional)):
    """根路径重定向到报告页"""
    target = "/reports"
    return RedirectResponse(url=target)
