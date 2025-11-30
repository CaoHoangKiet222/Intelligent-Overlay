from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from shared.contracts import ContextChunk, SpanRef


class RetrievalMode(str, Enum):
	VECTOR = "vector"
	LEXICAL = "lexical"
	HYBRID = "hybrid"


class RetrievalSearchRequest(BaseModel):
	context_id: str
	query: str = Field(min_length=1)
	top_k: int = Field(default=5, ge=1, le=50)
	mode: RetrievalMode = RetrievalMode.HYBRID
	alpha: float = Field(default=0.7, ge=0.0, le=1.0)


class RetrievalSpan(BaseModel):
	span: SpanRef
	snippet: str
	score: float
	breakdown: Dict[str, float] = Field(default_factory=dict)


class RetrievalSearchResponse(BaseModel):
	context_id: str
	query: str
	mode: RetrievalMode
	top_k: int
	took_ms: int
	results: List[RetrievalSpan]


class ContextDetailResponse(BaseModel):
	context_id: str
	locale: Optional[str] = None
	chunk_count: int
	segments: List[ContextChunk] = Field(default_factory=list)
