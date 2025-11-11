from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class GenerationResult:
	text: str


@dataclass(frozen=True)
class EmbeddingResult:
	vectors: List[List[float]]


