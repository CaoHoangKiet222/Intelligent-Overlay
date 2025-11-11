from typing import List
from domain.models import GenerationResult, EmbeddingResult
from providers.base import BaseProvider


class OllamaProvider(BaseProvider):
	def __init__(self, api_key: str) -> None:
		self._api_key = api_key

	@property
	def name(self) -> str:
		return "ollama"

	@property
	def cost_per_1k_tokens(self) -> float:
		return 0.0

	@property
	def latency_ms_estimate(self) -> int:
		return 500

	@property
	def context_window(self) -> int:
		return 8192

	def generate(self, prompt: str) -> GenerationResult:
		return GenerationResult(text=f"[ollama] {prompt}")

	def embed(self, texts: List[str]) -> EmbeddingResult:
		vectors = [[float(len(t))] * 3 for t in texts]
		return EmbeddingResult(vectors=vectors)

	def count_tokens(self, text: str) -> int:
		return max(1, len(text) // 4)


