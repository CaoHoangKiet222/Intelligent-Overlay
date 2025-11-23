from typing import List
from domain.models import GenerationResult, EmbeddingResult
from providers.base import BaseProvider


class AnthropicProvider(BaseProvider):
	def __init__(self, api_key: str) -> None:
		self._api_key = api_key
		self._generation_model = "claude-3-sonnet-20240229"
		self._embedding_model = "claude-embedding-1"

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

	@property
	def generation_model(self) -> str:
		return self._generation_model

	@property
	def embedding_model(self) -> str:
		return self._embedding_model

	def generate(self, prompt: str) -> GenerationResult:
		text = f"[anthropic-mock] {prompt}"
		return GenerationResult(
			text=text,
			model=self._generation_model,
			tokens_in=self.count_tokens(prompt),
			tokens_out=self.count_tokens(text),
			latency_ms=self.latency_ms_estimate,
		)

	def embed(self, texts: List[str]) -> EmbeddingResult:
		vectors = [[float(len(t))] * 3 for t in texts]
		return EmbeddingResult(vectors=vectors, model=self._embedding_model)

	def count_tokens(self, text: str) -> int:
		return max(1, len(text) // 4)
