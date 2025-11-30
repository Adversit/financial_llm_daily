"""Add finance_relevance and update layer enum

Revision ID: add_finance_relevance
Revises: c89b568287b0
Create Date: 2025-11-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_finance_relevance'
down_revision: Union[str, None] = 'c89b568287b0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    升级操作：
    1. 添加 finance_relevance 字段到 extraction_items 表
    2. 更新 layer 枚举值（POLITICS→金融政策监管，ECONOMY→金融经济，FINTECH→金融科技应用，FINTECH_AI→金融大模型技术，UNKNOWN→未知）
    """

    # 1. 添加 finance_relevance 字段（nullable，默认值为1.0）
    op.add_column('extraction_items',
                  sa.Column('finance_relevance', sa.Float(), nullable=True,
                           comment='金融相关性评分(0-1)'))

    # 为现有数据设置默认值
    op.execute("UPDATE extraction_items SET finance_relevance = 1.0 WHERE finance_relevance IS NULL")

    # 添加索引
    op.create_index('idx_extraction_items_finance_relevance', 'extraction_items', ['finance_relevance'])

    # 2. 更新 layer 枚举值
    # PostgreSQL 枚举类型更新需要特殊处理

    # 创建新的枚举类型
    op.execute("CREATE TYPE layer_new AS ENUM ('金融政策监管', '金融经济', '金融大模型技术', '金融科技应用', '未知')")

    # 将列类型更改为 TEXT，然后更新值，最后改为新枚举类型
    op.execute("ALTER TABLE extraction_items ALTER COLUMN layer TYPE TEXT")

    # 更新英文值到中文值
    op.execute("UPDATE extraction_items SET layer = '金融政策监管' WHERE layer = 'POLITICS'")
    op.execute("UPDATE extraction_items SET layer = '金融经济' WHERE layer = 'ECONOMY'")
    op.execute("UPDATE extraction_items SET layer = '金融科技应用' WHERE layer = 'FINTECH'")
    op.execute("UPDATE extraction_items SET layer = '金融大模型技术' WHERE layer = 'FINTECH_AI'")
    op.execute("UPDATE extraction_items SET layer = '未知' WHERE layer = 'UNKNOWN'")

    # 删除旧的枚举类型
    op.execute("DROP TYPE layer")

    # 重命名新枚举类型
    op.execute("ALTER TYPE layer_new RENAME TO layer")

    # 将列类型改回枚举
    op.execute("ALTER TABLE extraction_items ALTER COLUMN layer TYPE layer USING layer::layer")


def downgrade() -> None:
    """
    降级操作：
    1. 删除 finance_relevance 字段
    2. 还原 layer 枚举值
    """

    # 2. 还原 layer 枚举值（先做这个，因为涉及类型转换）
    # 创建旧的枚举类型
    op.execute("CREATE TYPE layer_old AS ENUM ('POLITICS', 'ECONOMY', 'FINTECH_AI', 'FINTECH', 'UNKNOWN')")

    # 将列类型更改为 TEXT
    op.execute("ALTER TABLE extraction_items ALTER COLUMN layer TYPE TEXT")

    # 还原中文值到英文值
    op.execute("UPDATE extraction_items SET layer = 'POLITICS' WHERE layer = '金融政策监管'")
    op.execute("UPDATE extraction_items SET layer = 'ECONOMY' WHERE layer = '金融经济'")
    op.execute("UPDATE extraction_items SET layer = 'FINTECH' WHERE layer = '金融科技应用'")
    op.execute("UPDATE extraction_items SET layer = 'FINTECH_AI' WHERE layer = '金融大模型技术'")
    op.execute("UPDATE extraction_items SET layer = 'UNKNOWN' WHERE layer = '未知'")

    # 删除新的枚举类型
    op.execute("DROP TYPE layer")

    # 重命名旧枚举类型
    op.execute("ALTER TYPE layer_old RENAME TO layer")

    # 将列类型改回枚举
    op.execute("ALTER TABLE extraction_items ALTER COLUMN layer TYPE layer USING layer::layer")

    # 1. 删除索引和字段
    op.drop_index('idx_extraction_items_finance_relevance', table_name='extraction_items')
    op.drop_column('extraction_items', 'finance_relevance')
