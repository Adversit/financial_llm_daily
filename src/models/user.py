"""
用户与偏好/规则相关模型
"""
from __future__ import annotations

import enum
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum as SQLEnum,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from .base import Base, TimestampMixin


class UserRole(str, enum.Enum):
    """系统用户角色"""

    ADMIN = "admin"
    USER = "user"


class User(Base, TimestampMixin):
    """用户表，管理员可设置密码，普通用户使用 OTP"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(200), nullable=False, unique=True, comment="邮箱")
    role = Column(
        SQLEnum(UserRole, native_enum=True, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=UserRole.USER,
        comment="角色",
    )
    is_active = Column(Boolean, default=True, nullable=False, comment="是否激活")
    last_login_at = Column(DateTime, nullable=True, comment="最后登录时间")
    hashed_password = Column(String(200), nullable=True, comment="管理员密码哈希")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"


class PreferenceScope(str, enum.Enum):
    """用户偏好作用范围"""

    DAILY = "daily"
    ARTICLE = "article"


class UserPreference(Base, TimestampMixin):
    """用户自定义提示词模板"""

    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_email = Column(String(200), nullable=False, comment="用户邮箱")
    name = Column(String(100), nullable=False, comment="模板名称")
    scope = Column(
        SQLEnum(PreferenceScope, native_enum=True, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        comment="作用范围",
    )
    prompt_text = Column(Text, nullable=False, comment="提示词内容")
    is_default = Column(Boolean, default=False, nullable=False, comment="是否默认模板")

    __table_args__ = (
        Index("idx_user_preferences_email", "user_email"),
        UniqueConstraint("user_email", "name", name="uq_user_email_name"),
    )

    def __repr__(self) -> str:
        return f"<UserPreference(id={self.id}, email={self.user_email}, name={self.name})>"


class RuleType(str, enum.Enum):
    """关注/屏蔽规则类型"""

    SOURCE = "source"
    KEYWORD = "keyword"


class WatchlistRule(Base, TimestampMixin):
    """关注清单规则"""

    __tablename__ = "watchlist_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(
        SQLEnum(RuleType, native_enum=True, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        comment="规则类型",
    )
    pattern = Column(String(200), nullable=False, comment="匹配模式")
    created_by = Column(String(200), nullable=False, comment="创建者邮箱")
    is_enabled = Column(Boolean, default=True, nullable=False, comment="是否启用")
    priority = Column(Integer, default=0, nullable=False, comment="优先级（数字越大越靠前）")

    __table_args__ = (Index("idx_watchlist_enabled", "is_enabled"),)

    def __repr__(self) -> str:
        return f"<WatchlistRule(id={self.id}, type={self.type}, pattern={self.pattern})>"


class BlocklistRule(Base, TimestampMixin):
    """黑名单规则"""

    __tablename__ = "blocklist_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(
        SQLEnum(RuleType, native_enum=True, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        comment="规则类型",
    )
    pattern = Column(String(200), nullable=False, comment="匹配模式")
    created_by = Column(String(200), nullable=False, comment="创建者邮箱")
    is_enabled = Column(Boolean, default=True, nullable=False, comment="是否启用")
    reason = Column(String(500), nullable=True, comment="屏蔽原因")

    __table_args__ = (Index("idx_blocklist_enabled", "is_enabled"),)

    def __repr__(self) -> str:
        return f"<BlocklistRule(id={self.id}, type={self.type}, pattern={self.pattern})>"


class NoteScope(str, enum.Enum):
    """备注作用范围"""

    GLOBAL = "global"
    SECTION = "section"


class ReportNote(Base, TimestampMixin):
    """日报备注"""

    __tablename__ = "report_notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_date = Column(Date, nullable=False, comment="报告日期")
    scope = Column(
        SQLEnum(NoteScope, native_enum=True, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        comment="范围",
    )
    section_key = Column(String(100), nullable=True, comment="分区键")
    author_email = Column(String(200), nullable=False, comment="作者邮箱")
    content_md = Column(Text, nullable=False, comment="备注内容（Markdown）")

    __table_args__ = (Index("idx_report_notes_date", "report_date"),)

    def __repr__(self) -> str:
        return f"<ReportNote(id={self.id}, date={self.report_date}, scope={self.scope})>"
