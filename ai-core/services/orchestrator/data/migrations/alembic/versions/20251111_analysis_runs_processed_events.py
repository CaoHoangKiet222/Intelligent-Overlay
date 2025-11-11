"""create analysis_runs and processed_events"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20251111_analysis_runs_processed_events"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
	op.create_table(
		"analysis_runs",
		sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
		sa.Column("event_id", sa.String(length=64), nullable=False, unique=True),
		sa.Column("bundle_id", postgresql.UUID(as_uuid=True), nullable=True),
		sa.Column("status", sa.String(length=16), nullable=False),
		sa.Column("summary_json", postgresql.JSONB(), nullable=True),
		sa.Column("argument_json", postgresql.JSONB(), nullable=True),
		sa.Column("sentiment_json", postgresql.JSONB(), nullable=True),
		sa.Column("logic_bias_json", postgresql.JSONB(), nullable=True),
		sa.Column("citations", postgresql.JSONB(), nullable=True),
		sa.Column("error_summary", sa.Text(), nullable=True),
		sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
	)
	op.create_table(
		"processed_events",
		sa.Column("event_id", sa.String(length=64), primary_key=True, nullable=False),
		sa.Column("processed_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
	)


def downgrade() -> None:
	op.drop_table("processed_events")
	op.drop_table("analysis_runs")


