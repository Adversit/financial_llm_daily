"""
FastAPI SSR 应用装配
"""
from __future__ import annotations

from pathlib import Path
from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from loguru import logger

from src.config.settings import settings
from .routes import assets, auth as auth_routes
from .routes import home, preferences, reports, stats
from .routes.admin import router as admin_router

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"


def _compile_origins(raw: str) -> List[str]:
    """将逗号分隔的 Origin 字符串转换为列表"""
    if raw.strip() == "*":
        return ["*"]
    origins = [item.strip() for item in raw.split(",") if item.strip()]
    return origins or ["*"]


def create_app() -> FastAPI:
    """创建 Web FastAPI 应用"""
    app = FastAPI(
        title="金融情报日报 · 管理台",
        description="Financial Intelligence Daily Report Web Portal",
        version="2.0.0",
    )

    cors_origins = _compile_origins(settings.CORS_ORIGINS)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    templates.env.globals["THEME_PRIMARY_COLOR"] = settings.THEME_PRIMARY_COLOR
    app.state.templates = templates

    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    else:
        logger.warning("Static directory not found: {}", STATIC_DIR)

    app.include_router(auth_routes.router)
    app.include_router(home.router)
    app.include_router(reports.router)
    app.include_router(preferences.router)
    app.include_router(stats.router)
    app.include_router(assets.router)
    app.include_router(admin_router)

    @app.get("/healthz", tags=["Health"])
    async def healthz():
        return {"status": "ok"}

    return app


app = create_app()
