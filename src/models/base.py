"""
SQLAlchemy 基础模型
"""
from sqlalchemy import Column, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import create_engine

from src.utils.time_utils import get_local_now_naive

Base = declarative_base()


class TimestampMixin:
    """时间戳混入类"""
    created_at = Column(DateTime, default=get_local_now_naive, nullable=False)
    updated_at = Column(DateTime, default=get_local_now_naive, onupdate=get_local_now_naive, nullable=False)
