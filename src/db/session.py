"""
数据库会话管理
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import NullPool
from contextlib import contextmanager
from loguru import logger
from src.config.settings import settings


# 创建引擎
engine = create_engine(
    settings.DATABASE_URL,
    echo=False,  # 生产环境设为False
    pool_pre_ping=True,  # 自动检查连接有效性
    poolclass=NullPool,  # 开发环境可使用NullPool,生产环境建议使用默认的QueuePool
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 线程安全的会话
ScopedSession = scoped_session(SessionLocal)


@contextmanager
def get_db_session():
    """
    获取数据库会话的上下文管理器

    用法:
        with get_db_session() as db:
            db.query(...)
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"数据库操作失败: {e}")
        raise
    finally:
        session.close()


def get_db():
    """
    FastAPI依赖注入用的数据库会话生成器

    用法:
        @app.get("/")
        def read_root(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    初始化数据库
    创建所有表结构
    """
    from src.models.base import Base
    from src.models import source, article, extraction, report, delivery, user, system

    logger.info("开始创建数据库表...")
    Base.metadata.create_all(bind=engine)
    logger.info("✅ 数据库表创建完成")


def drop_db():
    """
    删除所有表(谨慎使用)
    """
    from src.models.base import Base
    from src.models import source, article, extraction, report, delivery, user, system

    logger.warning("⚠️  正在删除所有数据库表...")
    Base.metadata.drop_all(bind=engine)
    logger.warning("❌ 所有表已删除")
