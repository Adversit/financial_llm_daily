"""
Celery 应用配置
"""

from celery import Celery
from celery.schedules import crontab

from src.config.settings import settings

# 创建 Celery 应用
celery_app = Celery(
    "fin_daily_report",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

# 配置 Celery
celery_app.conf.update(
    # 序列化
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # 时区
    timezone="Asia/Shanghai",
    enable_utc=False,

    # 任务路由
    task_routes={
        "src.tasks.crawl_tasks.*": {"queue": "crawl"},
        "src.tasks.extract_tasks.*": {"queue": "extract"},
        "src.tasks.report_tasks.*": {"queue": "report"},
        "src.tasks.mail_tasks.*": {"queue": "mail"},
    },

    # 任务结果过期时间
    result_expires=3600,

    # 任务时间限制
    task_time_limit=600,  # 10分钟硬限制
    task_soft_time_limit=540,  # 9分钟软限制

    # 任务重试
    task_acks_late=True,
    task_reject_on_worker_lost=True,

    # Worker 配置
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
)

# 定时任务配置
celery_app.conf.beat_schedule = {
    "daily-report-05:30": {
        "task": "src.tasks.orchestrator.run_daily_report",
        "schedule": crontab(hour=5, minute=30),  # 提前到 05:30，留出更多采集时间
        "args": (),
    },
}

# 自动发现任务模块
celery_app.autodiscover_tasks(
    [
        "src.tasks.crawl_tasks",
        "src.tasks.extract_tasks",
        "src.tasks.report_tasks",
        "src.tasks.mail_tasks",
        "src.tasks.orchestrator",
    ]
)
