"""
FastAPI 主应用

提供 API 接口和健康检查。
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from src.api.routes import health
from src.config.settings import settings

# 创建 FastAPI 应用

@asynccontextmanager
async def lifespan(_app: FastAPI):
    """应用生命周期管理"""
    logger.info("=" * 60)
    logger.info("🚀 FastAPI 应用启动")
    logger.info(f"   环境: {settings.ENV}")
    logger.info(f"   文档: http://localhost:8000/docs")
    logger.info(f"   健康检查: http://localhost:8000/healthz")
    logger.info("=" * 60)

    try:
        yield
    finally:
        logger.info("👋 FastAPI 应用关闭")


app = FastAPI(
    title="金融情报日报系统 API",
    description="Financial Intelligence Daily Report System API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(health.router, tags=["健康检查"])


@app.get("/")
async def root():
    """根路径"""
    return {
        "service": "金融情报日报系统",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/healthz"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
