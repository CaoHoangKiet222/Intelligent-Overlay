from __future__ import annotations

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict, PrivateAttr, field_validator


class SpanRef(BaseModel):
	model_config = ConfigDict(populate_by_name=True, extra="forbid")

	chunk_id: str = Field(alias="segment_id", serialization_alias="segment_id")
	start_offset: Optional[int] = Field(default=None, ge=0)
	end_offset: Optional[int] = Field(default=None, ge=0)
	sentence_index: Optional[int] = Field(default=None, ge=0)
	timestamp_start_ms: Optional[int] = Field(default=None, ge=0)
	timestamp_end_ms: Optional[int] = Field(default=None, ge=0)
	speaker_label: Optional[str] = None
	text_preview: Optional[str] = None
	score: Optional[float] = None


class ContextChunk(BaseModel):
	model_config = ConfigDict(populate_by_name=True, extra="forbid")

	chunk_id: str = Field(alias="segment_id", serialization_alias="segment_id")
	document_id: Optional[str] = None
	text: str
	start_offset: Optional[int] = Field(default=None, ge=0)
	end_offset: Optional[int] = Field(default=None, ge=0)
	sentence_index: Optional[int] = Field(default=None, ge=0)
	timestamp_start_ms: Optional[int] = Field(default=None, ge=0)
	timestamp_end_ms: Optional[int] = Field(default=None, ge=0)
	speaker_label: Optional[str] = None
	page_no: Optional[int] = Field(default=None, ge=0)
	paragraph_no: Optional[int] = Field(default=None, ge=0)
	metadata: Dict[str, Any] = Field(default_factory=dict)
	embedding: Optional[List[float]] = None
	embedding_model: Optional[str] = None
	embedding_dim: Optional[int] = Field(default=None, ge=1)

	@field_validator("end_offset")
	@classmethod
	def _validate_offsets(cls, end: Optional[int], values: Dict[str, Any]):
		start = values.get("start_offset")
		if end is not None and start is not None and end < start:
			raise ValueError("end_offset must be >= start_offset")
		return end

	def as_span(self) -> SpanRef:
		return SpanRef(
			chunk_id=self.chunk_id,
			start_offset=self.start_offset,
			end_offset=self.end_offset,
			sentence_index=self.sentence_index,
			timestamp_start_ms=self.timestamp_start_ms,
			timestamp_end_ms=self.timestamp_end_ms,
			speaker_label=self.speaker_label,
			text_preview=self.text[:200],
		)


class ContextBundle(BaseModel):
	model_config = ConfigDict(populate_by_name=True, extra="forbid")

	context_id: str
	raw_text: str
	locale: Optional[str] = "auto"
	source_url: Optional[str] = Field(default=None, alias="url", serialization_alias="url")
	source_type: Optional[str] = None
	metadata: Dict[str, Any] = Field(default_factory=dict)
	segments: List[ContextChunk] = Field(default_factory=list)

	_chunk_index: Dict[str, ContextChunk] = PrivateAttr(default_factory=dict)

	@field_validator("segments")
	@classmethod
	def _ensure_unique_chunks(cls, value: List[ContextChunk]):
		seen = set()
		for chunk in value:
			if chunk.chunk_id in seen:
				raise ValueError(f"duplicate chunk_id detected: {chunk.chunk_id}")
			seen.add(chunk.chunk_id)
		return value

	def _lazy_index(self) -> Dict[str, ContextChunk]:
		if len(self._chunk_index) != len(self.segments):
			self.rebuild_index()
		return self._chunk_index

	def rebuild_index(self) -> None:
		self._chunk_index = {chunk.chunk_id.lower(): chunk for chunk in self.segments}

	def add_chunk(self, chunk: ContextChunk) -> None:
		self.segments.append(chunk)
		self._chunk_index[chunk.chunk_id.lower()] = chunk

	def text_for_span(self, span: SpanRef) -> Optional[str]:
		chunk = self._lazy_index().get(span.chunk_id.lower())
		if not chunk:
			return None
		start = span.start_offset if span.start_offset is not None else chunk.start_offset
		end = span.end_offset if span.end_offset is not None else chunk.end_offset
		if start is None or end is None or start >= end:
			return chunk.text
		relative_start = start - (chunk.start_offset or 0)
		relative_end = end - (chunk.start_offset or 0)
		relative_start = max(0, relative_start)
		relative_end = max(relative_start, relative_end)
		return chunk.text[relative_start:relative_end]

