"""init schema with pgvector, enums, tables, indexes"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20251111_000001_init_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
	# Extensions
	op.execute("CREATE EXTENSION IF NOT EXISTS vector")

	# Enums
	source_type = sa.Enum("web", "pdf", "video", "text", name="source_type")
	chat_status = sa.Enum("active", "closed", name="chat_status")
	message_role = sa.Enum("system", "user", "assistant", "tool", name="message_role")
	llm_status = sa.Enum("success", "error", "timeout", name="llm_status")
	source_type.create(op.get_bind(), checkfirst=True)
	chat_status.create(op.get_bind(), checkfirst=True)
	message_role.create(op.get_bind(), checkfirst=True)
	llm_status.create(op.get_bind(), checkfirst=True)

	# prompts
	op.create_table(
		"prompts",
		sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
		sa.Column("key", sa.String(length=64), nullable=False, unique=True),
		sa.Column("name", sa.String(length=120), nullable=True),
		sa.Column("description", sa.Text(), nullable=True),
		sa.Column("tags", postgresql.JSONB(), nullable=True),
		sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
		sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
		sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
		sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
	)

	# prompt_versions
	op.create_table(
		"prompt_versions",
		sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
		sa.Column("prompt_id", postgresql.UUID(as_uuid=True), nullable=False),
		sa.Column("version", sa.Integer(), nullable=False),
		sa.Column("template", sa.Text(), nullable=False),
		sa.Column("variables", postgresql.JSONB(), nullable=True),
		sa.Column("input_schema", postgresql.JSONB(), nullable=True),
		sa.Column("output_schema", postgresql.JSONB(), nullable=True),
		sa.Column("notes", sa.Text(), nullable=True),
		sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
		sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
		sa.ForeignKeyConstraint(["prompt_id"], ["prompts.id"], ondelete="CASCADE"),
		sa.UniqueConstraint("prompt_id", "version", name="uq_prompt_versions_prompt_id_version"),
	)

	# documents
	op.create_table(
		"documents",
		sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
		sa.Column("source_type", source_type, nullable=False),
		sa.Column("source_url", sa.Text(), nullable=True),
		sa.Column("title", sa.Text(), nullable=True),
		sa.Column("locale", sa.String(length=10), nullable=True),
		sa.Column("content_hash", sa.CHAR(length=64), nullable=False, unique=True),
		sa.Column("metadata", postgresql.JSONB(), nullable=True),
		sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
		sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
	)

	# segments
	op.create_table(
		"segments",
		sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
		sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
		sa.Column("text", sa.Text(), nullable=False),
		sa.Column("start_offset", sa.Integer(), nullable=True),
		sa.Column("end_offset", sa.Integer(), nullable=True),
		sa.Column("speaker_label", sa.String(length=64), nullable=True),
		sa.Column("timestamp_start_ms", sa.Integer(), nullable=True),
		sa.Column("timestamp_end_ms", sa.Integer(), nullable=True),
		sa.Column("page_no", sa.Integer(), nullable=True),
		sa.Column("paragraph_no", sa.Integer(), nullable=True),
		sa.Column("sentence_no", sa.Integer(), nullable=True),
		sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
		sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
		sa.UniqueConstraint("document_id", "start_offset", "end_offset", name="uq_segments_doc_offsets"),
	)

	# embeddings (create without vector column first)
	op.create_table(
		"embeddings",
		sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
		sa.Column("segment_id", postgresql.UUID(as_uuid=True), nullable=False),
		sa.Column("model", sa.String(length=64), nullable=False),
		sa.Column("dim", sa.Integer(), nullable=False),
		sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
		sa.ForeignKeyConstraint(["segment_id"], ["segments.id"], ondelete="CASCADE"),
		sa.CheckConstraint("dim > 0", name="ck_embeddings_dim_positive"),
		sa.UniqueConstraint("segment_id", "model", name="uq_embeddings_segment_model"),
	)
	# add vector column and index using raw SQL to avoid extra deps
	op.execute("ALTER TABLE embeddings ADD COLUMN vector vector(1536) NOT NULL")
	op.execute(
		"CREATE INDEX IF NOT EXISTS idx_embeddings_vector_ivfflat ON embeddings USING ivfflat (vector vector_cosine_ops) WITH (lists = 100)"
	)

	# chat_sessions
	op.create_table(
		"chat_sessions",
		sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
		sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
		sa.Column("agent_type", sa.String(length=64), nullable=False),
		sa.Column("status", chat_status, nullable=False, server_default=sa.text("'active'::chat_status")),
		sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
		sa.Column("ended_at", sa.TIMESTAMP(timezone=True), nullable=True),
		sa.Column("meta", postgresql.JSONB(), nullable=True),
	)

	# chat_messages
	op.create_table(
		"chat_messages",
		sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
		sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
		sa.Column("role", message_role, nullable=False),
		sa.Column("content", sa.Text(), nullable=False),
		sa.Column("tokens_in", sa.Integer(), nullable=True),
		sa.Column("tokens_out", sa.Integer(), nullable=True),
		sa.Column("llm_call_id", postgresql.UUID(as_uuid=True), nullable=True),
		sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
		sa.ForeignKeyConstraint(["session_id"], ["chat_sessions.id"], ondelete="CASCADE"),
	)
	op.create_index(
		"ix_chat_messages_session_created_at",
		"chat_messages",
		["session_id", "created_at"],
		unique=False,
	)

	# llm_calls
	op.create_table(
		"llm_calls",
		sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
		sa.Column("provider", sa.String(length=32), nullable=False),
		sa.Column("model", sa.String(length=64), nullable=False),
		sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
		sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=True),
		sa.Column("prompt_version_id", postgresql.UUID(as_uuid=True), nullable=True),
		sa.Column("input", postgresql.JSONB(), nullable=False),
		sa.Column("output", postgresql.JSONB(), nullable=True),
		sa.Column("input_tokens", sa.Integer(), nullable=True),
		sa.Column("output_tokens", sa.Integer(), nullable=True),
		sa.Column("cost_usd", sa.Numeric(12, 6), nullable=True),
		sa.Column("latency_ms", sa.Integer(), nullable=True),
		sa.Column("status", llm_status, nullable=False, server_default=sa.text("'success'::llm_status")),
		sa.Column("error_message", sa.Text(), nullable=True),
		sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
		sa.ForeignKeyConstraint(["session_id"], ["chat_sessions.id"], ondelete="SET NULL"),
		sa.ForeignKeyConstraint(["message_id"], ["chat_messages.id"], ondelete="SET NULL"),
		sa.ForeignKeyConstraint(["prompt_version_id"], ["prompt_versions.id"], ondelete="SET NULL"),
	)
	op.create_index("ix_llm_calls_created_at", "llm_calls", ["created_at"], unique=False)
	op.create_index("ix_llm_calls_provider_model", "llm_calls", ["provider", "model"], unique=False)

	# feedbacks
	op.create_table(
		"feedbacks",
		sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
		sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
		sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=True),
		sa.Column("rating", sa.SmallInteger(), nullable=True),
		sa.Column("comment", sa.Text(), nullable=True),
		sa.Column("artifacts", postgresql.JSONB(), nullable=True),
		sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
		sa.ForeignKeyConstraint(["session_id"], ["chat_sessions.id"], ondelete="CASCADE"),
		sa.ForeignKeyConstraint(["message_id"], ["chat_messages.id"], ondelete="SET NULL"),
		sa.CheckConstraint("rating IS NULL OR (rating BETWEEN 1 AND 5)", name="ck_feedbacks_rating_range"),
	)

	# telemetry_metrics
	op.create_table(
		"telemetry_metrics",
		sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
		sa.Column("name", sa.String(length=64), nullable=False),
		sa.Column("labels", postgresql.JSONB(), nullable=True),
		sa.Column("value", sa.Float(precision=53), nullable=False),
		sa.Column("observed_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
	)
	# DESC index needs raw SQL for clarity
	op.execute("CREATE INDEX IF NOT EXISTS ix_telemetry_metrics_name_observed_at_desc ON telemetry_metrics (name, observed_at DESC)")

	# backrefs that require created tables
	op.create_foreign_key(
		"fk_chat_messages_llm_call",
		"chat_messages",
		"llm_calls",
		["llm_call_id"],
		["id"],
		ondelete="SET NULL",
	)


def downgrade() -> None:
	# Drop FKs created after tables
	op.drop_constraint("fk_chat_messages_llm_call", "chat_messages", type_="foreignkey")

	# Drop indexes and tables in reverse order
	op.execute("DROP INDEX IF EXISTS ix_telemetry_metrics_name_observed_at_desc")
	op.drop_table("telemetry_metrics")
	op.drop_table("feedbacks")
	op.drop_index("ix_llm_calls_provider_model", table_name="llm_calls")
	op.drop_index("ix_llm_calls_created_at", table_name="llm_calls")
	op.drop_table("llm_calls")
	op.drop_index("ix_chat_messages_session_created_at", table_name="chat_messages")
	op.drop_table("chat_messages")
	op.drop_table("chat_sessions")
	op.execute("DROP INDEX IF EXISTS idx_embeddings_vector_ivfflat")
	op.drop_table("embeddings")
	op.drop_table("segments")
	op.drop_table("documents")
	op.drop_table("prompt_versions")
	op.drop_table("prompts")

	# Enums
	for enum_name in ("llm_status", "message_role", "chat_status", "source_type"):
		op.execute(f"DROP TYPE IF EXISTS {enum_name}")

	# Extension can remain; no drop


