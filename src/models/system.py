"""
系统设置与审计日志模型
"""
from __future__ import annotations

from sqlalchemy import JSON, Column, DateTime, Index, Integer, String, Text

from src.utils.time_utils import get_local_now_naive

from .base import Base


class SystemSetting(Base):
    """系统设置（键值对形式）"""

    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), nullable=False, unique=True, comment="配置键")
    value_json = Column(JSON, nullable=True, comment="配置值(JSON)")
    description = Column(Text, nullable=True, comment="说明")
    updated_at = Column(DateTime, default=get_local_now_naive, onupdate=get_local_now_naive, nullable=False)

    def __repr__(self) -> str:
        return f"<SystemSetting(key={self.key})>"


class AdminAuditLog(Base):
    """管理员操作审计日志"""

    __tablename__ = "admin_audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    admin_email = Column(String(200), nullable=False, comment="管理员邮箱")
    action = Column(String(100), nullable=False, comment="操作类型")
    resource_type = Column(String(50), nullable=True, comment="资源类型")
    resource_id = Column(Integer, nullable=True, comment="资源 ID")
    before_json = Column(JSON, nullable=True, comment="操作前数据")
    after_json = Column(JSON, nullable=True, comment="操作后数据")
    ip_address = Column(String(50), nullable=True, comment="IP 地址")
    user_agent = Column(String(500), nullable=True, comment="User-Agent")
    created_at = Column(DateTime, default=get_local_now_naive, nullable=False)

    __table_args__ = (
        Index("idx_audit_email", "admin_email"),
        Index("idx_audit_action", "action"),
        Index("idx_audit_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<AdminAuditLog(id={self.id}, action={self.action})>"
