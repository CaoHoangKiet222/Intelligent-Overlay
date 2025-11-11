"""add pg_trgm extension and index on segments.text"""
from typing import Sequence, Union
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20251111_add_pg_trgm_index"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
	op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
	op.execute("CREATE INDEX IF NOT EXISTS ix_segments_text_trgm ON segments USING gin (text gin_trgm_ops)")


def downgrade() -> None:
	op.execute("DROP INDEX IF EXISTS ix_segments_text_trgm")


