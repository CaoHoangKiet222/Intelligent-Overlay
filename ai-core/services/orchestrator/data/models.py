from sqlalchemy import Column, String, Text, Integer, ForeignKey, UniqueConstraint, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP
from sqlalchemy.orm import relationship
import uuid
from .db import Base


class LlmCall(Base):
	__tablename__ = "llm_calls"
	id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
	provider = Column(String(32), nullable=False)
	model = Column(String(64), nullable=False)
	session_id = Column(UUID(as_uuid=True))
	message_id = Column(UUID(as_uuid=True))
	prompt_version_id = Column(UUID(as_uuid=True))
	input = Column(JSONB, nullable=False)
	output = Column(JSONB)
	input_tokens = Column(Integer)
	output_tokens = Column(Integer)
	cost_usd = Column(Integer)
	latency_ms = Column(Integer)
	status = Column(String(16), nullable=False)
	error_message = Column(Text)
	created_at = Column(TIMESTAMP(timezone=True))


class AnalysisRun(Base):
	__tablename__ = "analysis_runs"
	id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
	event_id = Column(String(64), unique=True, nullable=False)
	bundle_id = Column(UUID(as_uuid=True))
	callback_url = Column(String(512))
	status = Column(String(16), nullable=False)
	summary_json = Column(JSONB)
	argument_json = Column(JSONB)
	sentiment_json = Column(JSONB)
	logic_bias_json = Column(JSONB)
	citations = Column(JSONB)
	error_summary = Column(Text)
	created_at = Column(TIMESTAMP(timezone=True))


class ProcessedEvent(Base):
	__tablename__ = "processed_events"
	event_id = Column(String(64), primary_key=True)
	processed_at = Column(TIMESTAMP(timezone=True))


