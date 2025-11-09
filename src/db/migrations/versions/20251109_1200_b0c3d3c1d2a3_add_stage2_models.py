"""add_stage2_models

Revision ID: b0c3d3c1d2a3
Revises: f12c8fd3fab5
Create Date: 2025-11-09 12:00:00.000000

"""
from __future__ import annotations

from datetime import datetime
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import bcrypt


# revision identifiers, used by Alembic.
revision: str = "b0c3d3c1d2a3"
down_revision: Union[str, None] = "f12c8fd3fab5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


DEFAULT_ADMIN_EMAIL = "xtyydsf@system"
DEFAULT_ADMIN_PASSWORD = "xtyydsf"


def _hash_password(password: str) -> str:
    """使用bcrypt哈希密码（直接使用bcrypt库避免passlib兼容问题）"""
    if not password:
        password = ""
    # bcrypt.hashpw需要bytes输入
    password_bytes = password.encode("utf-8")
    # 生成salt并哈希
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    # 返回字符串形式
    return hashed.decode("utf-8")


def upgrade() -> None:
    """创建阶段二新增的用户/配置/审计相关表"""

    user_role_enum = sa.Enum("admin", "user", name="userrole")
    preference_scope_enum = sa.Enum("daily", "article", name="preferencescope")
    rule_type_enum = sa.Enum("source", "keyword", name="ruletype")
    note_scope_enum = sa.Enum("global", "section", name="notescope")

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(length=200), nullable=False, unique=True),
        sa.Column("role", user_role_enum, nullable=False, server_default=sa.text("'user'")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.Column("hashed_password", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "user_preferences",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_email", sa.String(length=200), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("scope", preference_scope_enum, nullable=False),
        sa.Column("prompt_text", sa.Text(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_email", "name", name="uq_user_email_name"),
    )
    op.create_index("idx_user_preferences_email", "user_preferences", ["user_email"])

    op.create_table(
        "watchlist_rules",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("type", rule_type_enum, nullable=False),
        sa.Column("pattern", sa.String(length=200), nullable=False),
        sa.Column("created_by", sa.String(length=200), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("priority", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("idx_watchlist_enabled", "watchlist_rules", ["is_enabled"])

    op.create_table(
        "blocklist_rules",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("type", rule_type_enum, nullable=False),
        sa.Column("pattern", sa.String(length=200), nullable=False),
        sa.Column("created_by", sa.String(length=200), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("idx_blocklist_enabled", "blocklist_rules", ["is_enabled"])

    op.create_table(
        "report_notes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("scope", note_scope_enum, nullable=False),
        sa.Column("section_key", sa.String(length=100), nullable=True),
        sa.Column("author_email", sa.String(length=200), nullable=False),
        sa.Column("content_md", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("idx_report_notes_date", "report_notes", ["report_date"])

    op.create_table(
        "system_settings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("key", sa.String(length=100), nullable=False, unique=True),
        sa.Column("value_json", sa.JSON(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "admin_audit_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("admin_email", sa.String(length=200), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource_type", sa.String(length=50), nullable=True),
        sa.Column("resource_id", sa.Integer(), nullable=True),
        sa.Column("before_json", sa.JSON(), nullable=True),
        sa.Column("after_json", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(length=50), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("idx_audit_email", "admin_audit_log", ["admin_email"])
    op.create_index("idx_audit_action", "admin_audit_log", ["action"])
    op.create_index("idx_audit_created_at", "admin_audit_log", ["created_at"])

    # 初始化数据
    now = datetime.utcnow()
    admin_password_hash = _hash_password(DEFAULT_ADMIN_PASSWORD)

    users_table = sa.table(
        "users",
        sa.column("email", sa.String()),
        sa.column("role", sa.String()),
        sa.column("is_active", sa.Boolean()),
        sa.column("last_login_at", sa.DateTime()),
        sa.column("hashed_password", sa.String()),
        sa.column("created_at", sa.DateTime()),
        sa.column("updated_at", sa.DateTime()),
    )
    op.bulk_insert(
        users_table,
        [
            {
                "email": DEFAULT_ADMIN_EMAIL,
                "role": "admin",
                "is_active": True,
                "last_login_at": None,
                "hashed_password": admin_password_hash,
                "created_at": now,
                "updated_at": now,
            }
        ],
    )

    system_settings_table = sa.table(
        "system_settings",
        sa.column("key", sa.String()),
        sa.column("value_json", sa.JSON()),
        sa.column("description", sa.Text()),
        sa.column("updated_at", sa.DateTime()),
    )
    settings_defaults = [
        {"key": "report_topn", "value_json": 5, "description": "报告正文每区 TopN"},
        {"key": "confidence_threshold", "value_json": 0.6, "description": "事实观点置信度阈值"},
        {"key": "min_content_len", "value_json": 120, "description": "最小内容长度"},
        {"key": "theme_color", "value_json": "#1d4ed8", "description": "管理台主题色"},
        {"key": "stopwords", "value_json": ["的", "是", "在"], "description": "默认停用词"},
        {"key": "daily_prompt_overrides", "value_json": {}, "description": "按日覆盖的提示词"},
        {"key": "admin_password_hash", "value_json": admin_password_hash, "description": "管理员密码哈希"},
    ]
    op.bulk_insert(
        system_settings_table,
        [{**row, "updated_at": now} for row in settings_defaults],
    )


def downgrade() -> None:
    """回滚阶段二新增的所有表和类型"""

    op.drop_index("idx_audit_created_at", table_name="admin_audit_log")
    op.drop_index("idx_audit_action", table_name="admin_audit_log")
    op.drop_index("idx_audit_email", table_name="admin_audit_log")
    op.drop_table("admin_audit_log")

    op.drop_table("system_settings")

    op.drop_index("idx_report_notes_date", table_name="report_notes")
    op.drop_table("report_notes")

    op.drop_index("idx_blocklist_enabled", table_name="blocklist_rules")
    op.drop_table("blocklist_rules")

    op.drop_index("idx_watchlist_enabled", table_name="watchlist_rules")
    op.drop_table("watchlist_rules")

    op.drop_index("idx_user_preferences_email", table_name="user_preferences")
    op.drop_table("user_preferences")

    op.drop_table("users")

    # 删除枚举类型
    bind = op.get_bind()
    sa.Enum(name="notescope").drop(bind, checkfirst=True)
    sa.Enum(name="ruletype").drop(bind, checkfirst=True)
    sa.Enum(name="preferencescope").drop(bind, checkfirst=True)
    sa.Enum(name="userrole").drop(bind, checkfirst=True)
