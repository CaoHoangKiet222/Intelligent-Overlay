"""add activation source types to source_type enum"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "20250101_000002_add_activation_source_types"
down_revision: Union[str, None] = "20251111_000001_init_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
	op.execute("ALTER TYPE source_type ADD VALUE IF NOT EXISTS 'browser'")
	op.execute("ALTER TYPE source_type ADD VALUE IF NOT EXISTS 'share'")
	op.execute("ALTER TYPE source_type ADD VALUE IF NOT EXISTS 'selection'")
	op.execute("ALTER TYPE source_type ADD VALUE IF NOT EXISTS 'bubble'")
	op.execute("ALTER TYPE source_type ADD VALUE IF NOT EXISTS 'backtap'")
	op.execute("ALTER TYPE source_type ADD VALUE IF NOT EXISTS 'noti'")
	op.execute("ALTER TYPE source_type ADD VALUE IF NOT EXISTS 'image'")
	op.execute("ALTER TYPE source_type ADD VALUE IF NOT EXISTS 'transcript'")


def downgrade() -> None:
	pass

