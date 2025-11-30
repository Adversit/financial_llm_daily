"""update_region_enum_to_chinese

Revision ID: 8374c14c25df
Revises: add_finance_relevance
Create Date: 2025-11-08 17:33:11.044149

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8374c14c25df'
down_revision: Union[str, None] = 'add_finance_relevance'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    将 region 枚举从英文更新为中文
    DOMESTIC -> 国内
    FOREIGN -> 国外
    UNKNOWN -> 未知
    """
    # 创建新的枚举类型
    op.execute("CREATE TYPE region_new AS ENUM ('国内', '国外', '未知')")

    # 将 extraction_items 表的 region 列类型更改为 TEXT
    op.execute("ALTER TABLE extraction_items ALTER COLUMN region TYPE TEXT")

    # 更新英文值到中文值
    op.execute("UPDATE extraction_items SET region = '国内' WHERE region = 'DOMESTIC'")
    op.execute("UPDATE extraction_items SET region = '国外' WHERE region = 'FOREIGN'")
    op.execute("UPDATE extraction_items SET region = '未知' WHERE region = 'UNKNOWN'")

    # 删除旧的枚举类型
    op.execute("DROP TYPE region")

    # 重命名新枚举类型
    op.execute("ALTER TYPE region_new RENAME TO region")

    # 将列类型改回枚举
    op.execute("ALTER TABLE extraction_items ALTER COLUMN region TYPE region USING region::region")


def downgrade() -> None:
    """
    将 region 枚举从中文还原为英文
    """
    # 创建旧的枚举类型
    op.execute("CREATE TYPE region_old AS ENUM ('DOMESTIC', 'FOREIGN', 'UNKNOWN')")

    # 将列类型更改为 TEXT
    op.execute("ALTER TABLE extraction_items ALTER COLUMN region TYPE TEXT")

    # 还原中文值到英文值
    op.execute("UPDATE extraction_items SET region = 'DOMESTIC' WHERE region = '国内'")
    op.execute("UPDATE extraction_items SET region = 'FOREIGN' WHERE region = '国外'")
    op.execute("UPDATE extraction_items SET region = 'UNKNOWN' WHERE region = '未知'")

    # 删除新的枚举类型
    op.execute("DROP TYPE region")

    # 重命名旧枚举类型
    op.execute("ALTER TYPE region_old RENAME TO region")

    # 将列类型改回枚举
    op.execute("ALTER TABLE extraction_items ALTER COLUMN region TYPE region USING region::region")
