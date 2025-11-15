from sqlalchemy import Column, String, Text, Integer, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP
from sqlalchemy.orm import relationship
import uuid
from .db import Base


class Document(Base):
	__tablename__ = "documents"
	id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
	source_type = Column(String(16), nullable=False)
	source_url = Column(Text)
	title = Column(Text)
	locale = Column(String(10))
	content_hash = Column(String(64))
	meta = Column("metadata", JSONB)  # Use 'meta' as Python attribute, 'metadata' as DB column name
	created_at = Column(TIMESTAMP(timezone=True))
	updated_at = Column(TIMESTAMP(timezone=True))


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
	created_at = Column(TIMESTAMP(timezone=True))


class Embedding(Base):
	__tablename__ = "embeddings"
	id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
	segment_id = Column(UUID(as_uuid=True), ForeignKey("segments.id", ondelete="CASCADE"), nullable=False)
	model = Column(String(64), nullable=False)
	dim = Column(Integer, nullable=False)
	created_at = Column(TIMESTAMP(timezone=True))
	# vector column created by migration; here omitted to avoid requiring pgvector dialect
	__table_args__ = (CheckConstraint("dim > 0", name="ck_embeddings_dim_positive"),)


