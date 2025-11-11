from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
	source_type: Literal["text", "pdf", "transcript"]
	text: Optional[str] = None
	transcript: Optional[List[Dict[str, Any]]] = None
	title: Optional[str] = None
	url: Optional[str] = None
	locale: Optional[str] = "auto"
	max_chars_per_segment: int = 1000
	overlap_chars: int = 100


class IngestResponse(BaseModel):
	document_id: str
	segments_created: int
	embedding_model: str
	dim: int


class SearchRequest(BaseModel):
	query: str
	alpha: float = Field(default=0.7, ge=0, le=1)
	top_k: int = 10
	vec_k: int = 100
	trgm_k: int = 200
	filter_document_ids: Optional[List[str]] = None


class SegmentResult(BaseModel):
	segment_id: str
	document_id: str
	text_preview: str
	start_offset: Optional[int] = None
	end_offset: Optional[int] = None
	page_no: Optional[int] = None
	paragraph_no: Optional[int] = None
	sentence_no: Optional[int] = None
	scores: Dict[str, float]
	local_span: Optional[Dict[str, int]] = None


class SearchResponse(BaseModel):
	took_ms: int
	results: List[SegmentResult]


