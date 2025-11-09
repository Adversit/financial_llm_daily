"""update_all_enums_to_lowercase

Revision ID: f12c8fd3fab5
Revises: 8374c14c25df
Create Date: 2025-11-08 17:40:00.846330

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f12c8fd3fab5'
down_revision: Union[str, None] = '8374c14c25df'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    将所有大写英文枚举值更新为小写
    """

    # 1. 更新 processingstatus
    op.execute("CREATE TYPE processingstatus_new AS ENUM ('raw', 'queued', 'running', 'done', 'failed', 'partial')")
    op.execute("ALTER TABLE articles ALTER COLUMN processing_status TYPE TEXT")
    op.execute("UPDATE articles SET processing_status = lower(processing_status)")
    op.execute("DROP TYPE processingstatus")
    op.execute("ALTER TYPE processingstatus_new RENAME TO processingstatus")
    op.execute("ALTER TABLE articles ALTER COLUMN processing_status TYPE processingstatus USING processing_status::processingstatus")

    # 2. 更新 queuestatus
    op.execute("CREATE TYPE queuestatus_new AS ENUM ('queued', 'running', 'done', 'failed')")
    op.execute("ALTER TABLE extraction_queue ALTER COLUMN status TYPE TEXT")
    op.execute("UPDATE extraction_queue SET status = lower(status)")
    op.execute("DROP TYPE queuestatus")
    op.execute("ALTER TYPE queuestatus_new RENAME TO queuestatus")
    op.execute("ALTER TABLE extraction_queue ALTER COLUMN status TYPE queuestatus USING status::queuestatus")

    # 3. 更新 deliverystatus
    op.execute("CREATE TYPE deliverystatus_new AS ENUM ('ok', 'failed', 'partial')")
    op.execute("ALTER TABLE delivery_log ALTER COLUMN status TYPE TEXT")
    op.execute("UPDATE delivery_log SET status = lower(status)")
    op.execute("DROP TYPE deliverystatus")
    op.execute("ALTER TYPE deliverystatus_new RENAME TO deliverystatus")
    op.execute("ALTER TABLE delivery_log ALTER COLUMN status TYPE deliverystatus USING status::deliverystatus")

    # 4. 更新 recipienttype
    op.execute("CREATE TYPE recipienttype_new AS ENUM ('whitelist', 'recipient')")
    op.execute("ALTER TABLE report_recipients ALTER COLUMN type TYPE TEXT")
    op.execute("UPDATE report_recipients SET type = lower(type)")
    op.execute("DROP TYPE recipienttype")
    op.execute("ALTER TYPE recipienttype_new RENAME TO recipienttype")
    op.execute("ALTER TABLE report_recipients ALTER COLUMN type TYPE recipienttype USING type::recipienttype")

    # 5. 更新 regionhint
    op.execute("CREATE TYPE regionhint_new AS ENUM ('国内', '国外', '未知')")
    op.execute("ALTER TABLE sources ALTER COLUMN region_hint TYPE TEXT")
    op.execute("UPDATE sources SET region_hint = CASE region_hint WHEN 'DOMESTIC' THEN '国内' WHEN 'FOREIGN' THEN '国外' WHEN 'UNKNOWN' THEN '未知' END")
    op.execute("DROP TYPE regionhint")
    op.execute("ALTER TYPE regionhint_new RENAME TO regionhint")
    op.execute("ALTER TABLE sources ALTER COLUMN region_hint TYPE regionhint USING region_hint::regionhint")

    # 6. 更新 sourcetype
    op.execute("CREATE TYPE sourcetype_new AS ENUM ('rss', 'static', 'dynamic')")
    op.execute("ALTER TABLE sources ALTER COLUMN type TYPE TEXT")
    op.execute("UPDATE sources SET type = lower(type)")
    op.execute("DROP TYPE sourcetype")
    op.execute("ALTER TYPE sourcetype_new RENAME TO sourcetype")
    op.execute("ALTER TABLE sources ALTER COLUMN type TYPE sourcetype USING type::sourcetype")


def downgrade() -> None:
    """
    还原所有枚举值为大写
    """

    # 1. 还原 processingstatus
    op.execute("CREATE TYPE processingstatus_old AS ENUM ('RAW', 'QUEUED', 'RUNNING', 'DONE', 'FAILED', 'PARTIAL')")
    op.execute("ALTER TABLE articles ALTER COLUMN processing_status TYPE TEXT")
    op.execute("UPDATE articles SET processing_status = upper(processing_status)")
    op.execute("DROP TYPE processingstatus")
    op.execute("ALTER TYPE processingstatus_old RENAME TO processingstatus")
    op.execute("ALTER TABLE articles ALTER COLUMN processing_status TYPE processingstatus USING processing_status::processingstatus")

    # 2. 还原 queuestatus
    op.execute("CREATE TYPE queuestatus_old AS ENUM ('QUEUED', 'RUNNING', 'DONE', 'FAILED')")
    op.execute("ALTER TABLE extraction_queue ALTER COLUMN status TYPE TEXT")
    op.execute("UPDATE extraction_queue SET status = upper(status)")
    op.execute("DROP TYPE queuestatus")
    op.execute("ALTER TYPE queuestatus_old RENAME TO queuestatus")
    op.execute("ALTER TABLE extraction_queue ALTER COLUMN status TYPE queuestatus USING status::queuestatus")

    # 3. 还原 deliverystatus
    op.execute("CREATE TYPE deliverystatus_old AS ENUM ('OK', 'FAILED', 'PARTIAL')")
    op.execute("ALTER TABLE delivery_log ALTER COLUMN status TYPE TEXT")
    op.execute("UPDATE delivery_log SET status = upper(status)")
    op.execute("DROP TYPE deliverystatus")
    op.execute("ALTER TYPE deliverystatus_old RENAME TO deliverystatus")
    op.execute("ALTER TABLE delivery_log ALTER COLUMN status TYPE deliverystatus USING status::deliverystatus")

    # 4. 还原 recipienttype
    op.execute("CREATE TYPE recipienttype_old AS ENUM ('WHITELIST', 'RECIPIENT')")
    op.execute("ALTER TABLE report_recipients ALTER COLUMN type TYPE TEXT")
    op.execute("UPDATE report_recipients SET type = upper(type)")
    op.execute("DROP TYPE recipienttype")
    op.execute("ALTER TYPE recipienttype_old RENAME TO recipienttype")
    op.execute("ALTER TABLE report_recipients ALTER COLUMN type TYPE recipienttype USING type::recipienttype")

    # 5. 还原 regionhint
    op.execute("CREATE TYPE regionhint_old AS ENUM ('DOMESTIC', 'FOREIGN', 'UNKNOWN')")
    op.execute("ALTER TABLE sources ALTER COLUMN region_hint TYPE TEXT")
    op.execute("UPDATE sources SET region_hint = CASE region_hint WHEN '国内' THEN 'DOMESTIC' WHEN '国外' THEN 'FOREIGN' WHEN '未知' THEN 'UNKNOWN' END")
    op.execute("DROP TYPE regionhint")
    op.execute("ALTER TYPE regionhint_old RENAME TO regionhint")
    op.execute("ALTER TABLE sources ALTER COLUMN region_hint TYPE regionhint USING region_hint::regionhint")

    # 6. 还原 sourcetype
    op.execute("CREATE TYPE sourcetype_old AS ENUM ('RSS', 'STATIC', 'DYNAMIC')")
    op.execute("ALTER TABLE sources ALTER COLUMN type TYPE TEXT")
    op.execute("UPDATE sources SET type = upper(type)")
    op.execute("DROP TYPE sourcetype")
    op.execute("ALTER TYPE sourcetype_old RENAME TO sourcetype")
    op.execute("ALTER TABLE sources ALTER COLUMN type TYPE sourcetype USING type::sourcetype")
