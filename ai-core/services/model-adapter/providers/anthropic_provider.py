from typing import List
from domain.models import GenerationResult, EmbeddingResult
from providers.base import BaseProvider


class AnthropicProvider(BaseProvider):
	def __init__(self, api_key: str) -> None:
		self._api_key = api_key

	@property
	def name(self) -> str:
		return "anthropic"

	@property
	def cost_per_1k_tokens(self) -> float:
		return 0.8

	@property
	def latency_ms_estimate(self) -> int:
		return 900

	@property
	def context_window(self) -> int:
		return 200000

	def generate(self, prompt: str) -> GenerationResult:
		return GenerationResult(text=f"[anthropic] {prompt}")

	def embed(self, texts: List[str]) -> EmbeddingResult:
		vectors = [[float(len(t))] * 3 for t in texts]
		return EmbeddingResult(vectors=vectors)

	def count_tokens(self, text: str) -> int:
		return max(1, len(text) // 4)


