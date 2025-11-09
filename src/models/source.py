"""
信息源模型
"""
from sqlalchemy import Column, Integer, String, Boolean, Enum as SQLEnum, DateTime
from datetime import datetime
import enum
from .base import Base, TimestampMixin


class SourceType(str, enum.Enum):
    """信息源类型"""
    RSS = "rss"
    STATIC = "static"
    DYNAMIC = "dynamic"


class RegionHint(str, enum.Enum):
    """区域提示"""
    DOMESTIC = "国内"
    FOREIGN = "国外"
    UNKNOWN = "未知"


class Source(Base, TimestampMixin):
    """信息源表"""
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, comment="信息源名称")
    type = Column(SQLEnum(SourceType, native_enum=True, values_callable=lambda x: [e.value for e in x]), nullable=False, comment="信息源类型")
    url = Column(String(500), nullable=False, comment="信息源URL")
    enabled = Column(Boolean, default=True, nullable=False, comment="是否启用")
    concurrency = Column(Integer, default=1, comment="并发数")
    timeout_sec = Column(Integer, default=30, comment="超时秒数")
    parser = Column(String(50), nullable=True, comment="解析器名称")
    region_hint = Column(SQLEnum(RegionHint, native_enum=True, values_callable=lambda x: [e.value for e in x]), default=RegionHint.UNKNOWN, comment="区域提示")

    def __repr__(self):
        return f"<Source(id={self.id}, name={self.name}, type={self.type})>"
