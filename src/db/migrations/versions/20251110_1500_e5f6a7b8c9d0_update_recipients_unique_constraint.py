"""update_recipients_unique_constraint

Revision ID: e5f6a7b8c9d0
Revises: b0c3d3c1d2a3
Create Date: 2025-11-10 15:00:00.000000

说明：
- 移除 report_recipients 表的 email 唯一约束
- 添加 (email, type) 复合唯一索引
- 允许同一邮箱同时作为收件人和白名单

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "b0c3d3c1d2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """升级数据库"""
    # 1. 删除旧的唯一约束
    # PostgreSQL 中唯一约束会自动创建唯一索引，名称通常是 tablename_columnname_key
    op.drop_constraint('report_recipients_email_key', 'report_recipients', type_='unique')

    # 2. 创建新的复合唯一索引
    op.create_index(
        'idx_recipients_email_type',
        'report_recipients',
        ['email', 'type'],
        unique=True
    )

    print("✅ 迁移完成: report_recipients 表现在允许同一邮箱同时作为收件人和白名单")


def downgrade() -> None:
    """回滚数据库"""
    # 1. 删除复合唯一索引
    op.drop_index('idx_recipients_email_type', table_name='report_recipients')

    # 2. 恢复原有的 email 唯一约束
    # 注意：如果数据库中已有同一邮箱的多条记录，回滚会失败
    # 需要先手动清理重复数据
    op.create_unique_constraint('report_recipients_email_key', 'report_recipients', ['email'])

    print("⚠️  回滚完成: report_recipients 表恢复为 email 唯一约束")
