from sqlalchemy import CheckConstraint, Column, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
import uuid
import sys
from pathlib import Path
from .db import Base
import enum

ai_core_path = Path(__file__).parent.parent.parent.parent
if str(ai_core_path) not in sys.path:
	sys.path.insert(0, str(ai_core_path))

from shared.config.service_configs import RetrievalServiceConfig


class SourceType(str, enum.Enum):
	TEXT = "text"
	PDF = "pdf"
	TRANSCRIPT = "transcript"


class Document(Base):
	__tablename__ = "documents"
	id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
	source_type = Column(
		Enum(
			SourceType,
			name="source_type",
			values_callable=lambda enum_cls: [item.value for item in enum_cls],
			validate_strings=True,
		),
		nullable=False,
		default=SourceType.TEXT,
	)
	source_url = Column(Text)
	title = Column(Text)
	locale = Column(String(10))
	content_hash = Column(String(64))
	meta = Column("metadata", JSONB)  # Use 'meta' as Python attribute, 'metadata' as DB column name
	created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
	updated_at = Column(
		TIMESTAMP(timezone=True),
		nullable=False,
		server_default=func.now(),
		onupdate=func.now(),
	)


class Segment(Base):
	__tablename__ = "segments"
	id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
	document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
	text = Column(Text, nullable=False)
	start_offset = Column(Integer)
	end_offset = Column(Integer)
	speaker_label = Column(String(64))
	timestamp_start_ms = Column(Integer)
	timestamp_end_ms = Column(Integer)
	page_no = Column(Integer)
	paragraph_no = Column(Integer)
	sentence_no = Column(Integer)
	created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())


class Embedding(Base):
	__tablename__ = "embeddings"
	id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
	segment_id = Column(UUID(as_uuid=True), ForeignKey("segments.id", ondelete="CASCADE"), nullable=False)
	model = Column(String(64), nullable=False)
	dim = Column(Integer, nullable=False)
	created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
	vector = Column(Vector(16000), nullable=False)
	__table_args__ = (CheckConstraint("dim > 0", name="ck_embeddings_dim_positive"),)


