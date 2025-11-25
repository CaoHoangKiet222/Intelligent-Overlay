from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class GenerationResult:
	text: str
	model: str = ""
	tokens_in: Optional[int] = None
	tokens_out: Optional[int] = None
	latency_ms: Optional[int] = None


@dataclass(frozen=True)
class EmbeddingResult:
	vectors: List[List[float]]
	model: str
	dim: int | None = None


