from sqlalchemy import Column, String, Text, Boolean, Integer, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP
from sqlalchemy.orm import relationship
import uuid
from .db import Base


class Prompt(Base):
	__tablename__ = "prompts"
	id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
	key = Column(String(64), unique=True, nullable=False)
	name = Column(String(120), nullable=False)
	description = Column(Text)
	tags = Column(JSONB)
	is_active = Column(Boolean, default=True, nullable=False)
	created_by = Column(UUID(as_uuid=True))
	created_at = Column(
		TIMESTAMP(timezone=True),
		nullable=False,
		default=func.now(),
		server_default=func.now(),
	)
	updated_at = Column(
		TIMESTAMP(timezone=True),
		nullable=False,
		default=func.now(),
		server_default=func.now(),
		onupdate=func.now(),
	)
	versions = relationship("PromptVersion", backref="prompt", lazy="raise")


class PromptVersion(Base):
	__tablename__ = "prompt_versions"
	id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
	prompt_id = Column(UUID(as_uuid=True), ForeignKey("prompts.id", ondelete="CASCADE"), nullable=False)
	version = Column(Integer, nullable=False)
	template = Column(Text, nullable=False)
	variables = Column(JSONB)
	input_schema = Column(JSONB)
	output_schema = Column(JSONB)
	notes = Column(Text)
	created_by = Column(UUID(as_uuid=True))
	created_at = Column(
		TIMESTAMP(timezone=True),
		nullable=False,
		default=func.now(),
		server_default=func.now(),
	)
	__table_args__ = (UniqueConstraint("prompt_id", "version", name="uq_prompt_version"),)


