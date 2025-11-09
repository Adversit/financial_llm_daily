"""
管理员路由汇总
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.models.user import User
from src.web.deps import require_admin
from src.utils.time_utils import get_local_now_naive

from . import recipients, sources

# 主路由
router = APIRouter(prefix="/admin", tags=["Admin"])

# 注册子路由
router.include_router(sources.router, prefix="")
router.include_router(recipients.router, prefix="")


def _templates(request: Request):
    return request.app.state.templates


@router.get("", response_class=HTMLResponse)
async def admin_home(request: Request, current_user: User = Depends(require_admin)):
    """管理后台首页"""
    return _templates(request).TemplateResponse(
        "admin/index.html",
        {
            "request": request,
            "current_user": current_user,
            "page_title": "管理总览"
        }
    )


# 以下为占位路由,待后续实现

@router.get("/settings", response_class=HTMLResponse)
async def admin_settings(
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """系统设置页面 - 加载当前配置"""
    from src.models.system import SystemSetting

    # 读取所有设置
    settings = db.query(SystemSetting).all()
    settings_dict = {s.key: s.value_json for s in settings}

    # 提供默认值
    default_settings = {
        "report_topn": 5,
        "confidence_threshold": 0.6,
        "min_content_len": 120,
        "crawl_concurrency_rss": 10,
        "crawl_concurrency_web": 2,
        "llm_timeout_sec": 90,
        "llm_retries": 2,
        "smtp_host": "smtp.163.com",
        "smtp_port": 465,
        "mail_batch_limit": 50,
        "mail_rate_limit_per_sec": 1,
        "wordcloud_cache_ttl": 86400,  # 秒为单位,默认24小时
        "primary_color": "#2563eb",
        "secondary_color": "#1e4976",
        "accent_color": "#f59e0b",
        "provider_deepseek": "deepseek",
        "provider_qwen": "qwen"
    }

    # 合并设置 (数据库优先)
    for key, default_value in default_settings.items():
        if key not in settings_dict:
            settings_dict[key] = default_value

    # 为模板添加小时格式的缓存时长 (方便表单显示)
    settings_dict["wordcloud_cache_ttl_hours"] = settings_dict.get("wordcloud_cache_ttl", 86400) // 3600

    return _templates(request).TemplateResponse(
        "admin/settings.html",
        {
            "request": request,
            "current_user": current_user,
            "page_title": "系统设置",
            "settings": settings_dict
        }
    )


@router.post("/settings")
async def save_settings(
    request: Request,
    report_topn: int = Form(...),
    confidence_threshold: float = Form(...),
    min_content_len: int = Form(...),
    crawl_concurrency_rss: int = Form(...),
    crawl_concurrency_web: int = Form(...),
    llm_timeout_sec: int = Form(...),
    llm_retries: int = Form(...),
    smtp_host: str = Form(...),
    smtp_port: int = Form(...),
    mail_batch_limit: int = Form(...),
    mail_rate_limit_per_sec: int = Form(...),
    wordcloud_cache_ttl_hours: int = Form(...),
    primary_color: str = Form(...),
    secondary_color: str = Form(...),
    accent_color: str = Form(...),
    provider_deepseek: str = Form(...),
    provider_qwen: str = Form(...),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """保存系统设置"""
    from src.models.system import SystemSetting, AdminAuditLog

    # 定义所有设置项 (注意: wordcloud_cache_ttl需要转换为秒)
    settings_to_save = {
        "report_topn": report_topn,
        "confidence_threshold": confidence_threshold,
        "min_content_len": min_content_len,
        "crawl_concurrency_rss": crawl_concurrency_rss,
        "crawl_concurrency_web": crawl_concurrency_web,
        "llm_timeout_sec": llm_timeout_sec,
        "llm_retries": llm_retries,
        "smtp_host": smtp_host,
        "smtp_port": smtp_port,
        "mail_batch_limit": mail_batch_limit,
        "mail_rate_limit_per_sec": mail_rate_limit_per_sec,
        "wordcloud_cache_ttl": wordcloud_cache_ttl_hours * 3600,  # 转换为秒
        "primary_color": primary_color,
        "secondary_color": secondary_color,
        "accent_color": accent_color,
        "provider_deepseek": provider_deepseek,
        "provider_qwen": provider_qwen
    }

    # 记录修改前的值
    before_values = {}
    existing_settings = db.query(SystemSetting).all()
    for s in existing_settings:
        before_values[s.key] = s.value_json

    # 保存或更新每个设置项
    for key, value in settings_to_save.items():
        existing = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if existing:
            existing.value_json = value
            existing.updated_at = get_local_now_naive()
        else:
            new_setting = SystemSetting(
                key=key,
                value_json=value,
                description=f"系统配置项: {key}"
            )
            db.add(new_setting)

    # 记录审计日志
    audit_log = AdminAuditLog(
        admin_email=current_user.email,
        action="update_system_settings",
        resource_type="system_settings",
        resource_id=0,  # 系统设置没有具体ID
        before_json=before_values,
        after_json=settings_to_save,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        created_at=get_local_now_naive()
    )
    db.add(audit_log)

    db.commit()

    return RedirectResponse(url="/admin/settings", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/audit", response_class=HTMLResponse)
async def admin_audit(
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """操作审计日志页面"""
    from src.models.system import AdminAuditLog
    from datetime import datetime, timedelta

    # 获取查询参数
    action_filter = request.query_params.get("action")
    days = int(request.query_params.get("days", "7"))  # 默认显示最近7天

    # 构建查询
    query = db.query(AdminAuditLog)

    # 时间过滤
    since_date = datetime.now() - timedelta(days=days)
    query = query.filter(AdminAuditLog.created_at >= since_date)

    # 操作类型过滤
    if action_filter:
        query = query.filter(AdminAuditLog.action == action_filter)

    # 按时间倒序，限制数量
    logs = query.order_by(AdminAuditLog.created_at.desc()).limit(200).all()

    # 获取所有操作类型用于筛选器
    all_actions = db.query(AdminAuditLog.action).distinct().all()
    action_types = sorted([a[0] for a in all_actions if a[0]])

    return _templates(request).TemplateResponse(
        "admin/audit.html",
        {
            "request": request,
            "current_user": current_user,
            "page_title": "操作审计",
            "logs": logs,
            "action_types": action_types,
            "current_action": action_filter,
            "current_days": days
        }
    )


@router.get("/status", response_class=HTMLResponse)
async def admin_status(
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """系统状态监控页面"""
    import redis
    from sqlalchemy import text
    import os

    status_data = {
        "database": {"status": "unknown", "message": "", "details": {}},
        "redis": {"status": "unknown", "message": "", "details": {}},
        "celery": {"status": "unknown", "message": "", "details": {}},
        "web": {"status": "healthy", "message": "Web服务运行正常", "details": {}}
    }

    # 检查数据库
    try:
        result = db.execute(text("SELECT 1")).scalar()
        if result == 1:
            # 获取数据库统计
            from src.models.article import Article
            from src.models.report import Report
            from src.models.extraction import ExtractionItem

            article_count = db.query(Article).count()
            report_count = db.query(Report).count()
            extraction_count = db.query(ExtractionItem).count()

            status_data["database"]["status"] = "healthy"
            status_data["database"]["message"] = "数据库连接正常"
            status_data["database"]["details"] = {
                "articles": article_count,
                "reports": report_count,
                "extractions": extraction_count
            }
    except Exception as e:
        status_data["database"]["status"] = "error"
        status_data["database"]["message"] = f"数据库连接失败: {str(e)}"

    # 检查Redis
    try:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        r = redis.from_url(redis_url, decode_responses=True)
        r.ping()

        # 获取Redis信息
        info = r.info()
        status_data["redis"]["status"] = "healthy"
        status_data["redis"]["message"] = "Redis连接正常"
        status_data["redis"]["details"] = {
            "version": info.get("redis_version", "unknown"),
            "used_memory_human": info.get("used_memory_human", "unknown"),
            "connected_clients": info.get("connected_clients", 0)
        }
    except Exception as e:
        status_data["redis"]["status"] = "error"
        status_data["redis"]["message"] = f"Redis连接失败: {str(e)}"

    # 检查Celery (简化检查 - 检查Redis中的Celery队列)
    try:
        # 尝试从Redis获取Celery相关信息
        if status_data["redis"]["status"] == "healthy":
            # 这里可以检查Celery队列的长度等信息
            status_data["celery"]["status"] = "healthy"
            status_data["celery"]["message"] = "任务队列正常"
            status_data["celery"]["details"] = {
                "note": "基于Redis连接状态判断"
            }
        else:
            status_data["celery"]["status"] = "warning"
            status_data["celery"]["message"] = "无法检查Celery状态 (Redis不可用)"
    except Exception as e:
        status_data["celery"]["status"] = "error"
        status_data["celery"]["message"] = f"Celery检查失败: {str(e)}"

    return _templates(request).TemplateResponse(
        "admin/status.html",
        {
            "request": request,
            "current_user": current_user,
            "page_title": "系统状态",
            "status": status_data
        }
    )


@router.get("/usage", response_class=HTMLResponse)
async def admin_usage(
    request: Request,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Token费用统计"""
    from src.models.delivery import ProviderUsage
    from sqlalchemy import func
    from datetime import datetime, timedelta

    # 获取查询参数
    days = int(request.query_params.get("days", "7"))  # 默认显示最近7天

    # 时间过滤
    since_date = datetime.now() - timedelta(days=days)

    # 按Provider聚合统计
    provider_stats = (
        db.query(
            ProviderUsage.provider_name,
            func.sum(ProviderUsage.prompt_tokens).label("total_prompt_tokens"),
            func.sum(ProviderUsage.completion_tokens).label("total_completion_tokens"),
            func.sum(ProviderUsage.total_tokens).label("total_tokens"),
            func.sum(ProviderUsage.cost).label("total_cost"),
            func.count(ProviderUsage.id).label("call_count")
        )
        .filter(ProviderUsage.created_at >= since_date)
        .group_by(ProviderUsage.provider_name)
        .all()
    )

    # 按Provider和模型聚合统计
    model_stats = (
        db.query(
            ProviderUsage.provider_name,
            ProviderUsage.model_name,
            func.sum(ProviderUsage.prompt_tokens).label("total_prompt_tokens"),
            func.sum(ProviderUsage.completion_tokens).label("total_completion_tokens"),
            func.sum(ProviderUsage.total_tokens).label("total_tokens"),
            func.sum(ProviderUsage.cost).label("total_cost"),
            func.count(ProviderUsage.id).label("call_count")
        )
        .filter(ProviderUsage.created_at >= since_date)
        .group_by(ProviderUsage.provider_name, ProviderUsage.model_name)
        .all()
    )

    # 计算总计
    total_stats = {
        "total_tokens": sum(s.total_tokens or 0 for s in provider_stats),
        "total_cost": sum(s.total_cost or 0 for s in provider_stats),
        "call_count": sum(s.call_count or 0 for s in provider_stats)
    }

    # 组织数据结构
    providers_data = []
    for stat in provider_stats:
        provider_info = {
            "name": stat.provider_name,
            "total_tokens": stat.total_tokens or 0,
            "prompt_tokens": stat.total_prompt_tokens or 0,
            "completion_tokens": stat.total_completion_tokens or 0,
            "cost": stat.total_cost or 0,
            "call_count": stat.call_count or 0,
            "models": []
        }

        # 添加该provider下的模型统计
        for model_stat in model_stats:
            if model_stat.provider_name == stat.provider_name:
                provider_info["models"].append({
                    "name": model_stat.model_name,
                    "total_tokens": model_stat.total_tokens or 0,
                    "prompt_tokens": model_stat.total_prompt_tokens or 0,
                    "completion_tokens": model_stat.total_completion_tokens or 0,
                    "cost": model_stat.total_cost or 0,
                    "call_count": model_stat.call_count or 0
                })

        providers_data.append(provider_info)

    return _templates(request).TemplateResponse(
        "admin/usage.html",
        {
            "request": request,
            "current_user": current_user,
            "page_title": "费用统计",
            "providers": providers_data,
            "total_stats": total_stats,
            "current_days": days
        }
    )


@router.get("/watchlist", response_class=HTMLResponse)
async def admin_watchlist(request: Request, current_user: User = Depends(require_admin)):
    return _templates(request).TemplateResponse(
        "admin/index.html",
        {"request": request, "current_user": current_user, "page_title": "关注清单"}
    )


@router.get("/blocklist", response_class=HTMLResponse)
async def admin_blocklist(request: Request, current_user: User = Depends(require_admin)):
    return _templates(request).TemplateResponse(
        "admin/index.html",
        {"request": request, "current_user": current_user, "page_title": "屏蔽规则"}
    )


@router.get("/notes", response_class=HTMLResponse)
async def admin_notes(request: Request, current_user: User = Depends(require_admin)):
    return _templates(request).TemplateResponse(
        "admin/index.html",
        {"request": request, "current_user": current_user, "page_title": "运营备注"}
    )
