"""add parser_config field to sources table

Revision ID: playwright_parser_config
Revises: 20251113_0923_837428ba03f8
Create Date: 2025-11-13 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'playwright_parser_config'
down_revision: Union[str, None] = '837428ba03f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """添加 parser_config 字段到 sources 表"""
    op.add_column(
        'sources',
        sa.Column(
            'parser_config',
            sa.JSON(),
            nullable=True,
            comment='解析器配置JSON: {need_scroll, link_selectors, wait_selector, allow_patterns}'
        )
    )


def downgrade() -> None:
    """移除 parser_config 字段"""
    op.drop_column('sources', 'parser_config')
