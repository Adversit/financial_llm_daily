"""
健康检查路由

提供系统健康状态检查端点。
"""

from typing import Dict, Any

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from loguru import logger

from src.config.settings import settings
from src.utils.time_utils import get_local_now

router = APIRouter()


def check_database() -> Dict[str, Any]:
    """检查数据库连接"""
    try:
        from src.db.session import get_db
        from sqlalchemy import text

        db = next(get_db())
        result = db.execute(text("SELECT 1"))
        result.fetchone()

        return {"status": "ok", "message": "Database connection successful"}

    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {"status": "error", "message": str(e)}


def check_redis() -> Dict[str, Any]:
    """检查 Redis 连接"""
    try:
        import redis

        r = redis.from_url(settings.REDIS_URL)
        r.ping()

        return {"status": "ok", "message": "Redis connection successful"}

    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return {"status": "error", "message": str(e)}


def check_celery_workers() -> Dict[str, Any]:
    """检查 Celery Worker 状态"""
    try:
        from src.tasks.celery_app import celery_app

        # 获取活跃的 workers
        inspect = celery_app.control.inspect()
        active_workers = inspect.active()

        if active_workers:
            worker_count = len(active_workers)
            return {
                "status": "ok",
                "message": f"{worker_count} worker(s) active",
                "workers": list(active_workers.keys())
            }
        else:
            return {
                "status": "warning",
                "message": "No active workers found",
                "workers": []
            }

    except Exception as e:
        logger.error(f"Celery workers health check failed: {e}")
        return {"status": "error", "message": str(e)}


def check_disk_space() -> Dict[str, Any]:
    """检查磁盘空间"""
    try:
        import shutil

        total, used, free = shutil.disk_usage("/")

        # 计算使用率
        usage_percent = (used / total) * 100

        # 如果使用率超过 90%，发出警告
        if usage_percent > 90:
            status_val = "warning"
            message = f"Disk usage high: {usage_percent:.1f}%"
        else:
            status_val = "ok"
            message = f"Disk usage normal: {usage_percent:.1f}%"

        return {
            "status": status_val,
            "message": message,
            "total_gb": round(total / (1024 ** 3), 2),
            "used_gb": round(used / (1024 ** 3), 2),
            "free_gb": round(free / (1024 ** 3), 2),
            "usage_percent": round(usage_percent, 2)
        }

    except Exception as e:
        logger.error(f"Disk space health check failed: {e}")
        return {"status": "error", "message": str(e)}


@router.get("/healthz")
async def health_check():
    """
    健康检查端点

    返回系统各组件的健康状态：
    - database: 数据库连接
    - redis: Redis 连接
    - celery_workers: Celery Worker 状态
    - disk: 磁盘空间

    Returns:
        健康状态 JSON
    """
    checks = {
        "timestamp": get_local_now().isoformat(),
        "status": "ok",
        "checks": {
            "database": check_database(),
            "redis": check_redis(),
            "celery_workers": check_celery_workers(),
            "disk": check_disk_space(),
        }
    }

    # 判断整体状态
    component_statuses = [v["status"] for v in checks["checks"].values()]

    if "error" in component_statuses:
        checks["status"] = "error"
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE
    elif "warning" in component_statuses:
        checks["status"] = "warning"
        http_status = status.HTTP_200_OK
    else:
        checks["status"] = "ok"
        http_status = status.HTTP_200_OK

    return JSONResponse(content=checks, status_code=http_status)


@router.get("/healthz/simple")
async def simple_health_check():
    """
    简单健康检查端点

    仅检查服务是否运行，不检查依赖组件。
    用于负载均衡器的快速健康检查。

    Returns:
        简单状态 JSON
    """
    return {
        "status": "ok",
        "timestamp": get_local_now().isoformat()
    }


@router.get("/healthz/database")
async def database_health_check():
    """
    数据库健康检查端点

    Returns:
        数据库状态 JSON
    """
    result = check_database()

    if result["status"] == "ok":
        return JSONResponse(content=result, status_code=status.HTTP_200_OK)
    else:
        return JSONResponse(content=result, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)


@router.get("/healthz/redis")
async def redis_health_check():
    """
    Redis 健康检查端点

    Returns:
        Redis 状态 JSON
    """
    result = check_redis()

    if result["status"] == "ok":
        return JSONResponse(content=result, status_code=status.HTTP_200_OK)
    else:
        return JSONResponse(content=result, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)


@router.get("/healthz/celery")
async def celery_health_check():
    """
    Celery 健康检查端点

    Returns:
        Celery 状态 JSON
    """
    result = check_celery_workers()

    if result["status"] == "ok":
        return JSONResponse(content=result, status_code=status.HTTP_200_OK)
    elif result["status"] == "warning":
        return JSONResponse(content=result, status_code=status.HTTP_200_OK)
    else:
        return JSONResponse(content=result, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
