from typing import List
from domain.models import GenerationResult, EmbeddingResult
from providers.base import BaseProvider


class MistralProvider(BaseProvider):
	def __init__(self, api_key: str) -> None:
		self._api_key = api_key

	@property
	def name(self) -> str:
		return "mistral"

	@property
	def cost_per_1k_tokens(self) -> float:
		return 0.3

	@property
	def latency_ms_estimate(self) -> int:
		return 700

	@property
	def context_window(self) -> int:
		return 32000

	def generate(self, prompt: str) -> GenerationResult:
		return GenerationResult(text=f"[mistral] {prompt}")

	def embed(self, texts: List[str]) -> EmbeddingResult:
		vectors = [[float(len(t))] * 3 for t in texts]
		return EmbeddingResult(vectors=vectors)

	def count_tokens(self, text: str) -> int:
		return max(1, len(text) // 4)


