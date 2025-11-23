from typing import Dict, List

from domain.models import EmbeddingResult, GenerationResult
from providers.base import BaseProvider
from providers.registry import ProviderRegistry
from routing.policy import RouterPolicy


class DummyProvider(BaseProvider):
	def __init__(self, name: str, embedding_model: str) -> None:
		self._name = name
		self._embedding_model = embedding_model
		self._generation_model = f"{name}-gen"

	@property
	def name(self) -> str:
		return self._name

	@property
	def cost_per_1k_tokens(self) -> float:
		return 0.1

	@property
	def latency_ms_estimate(self) -> int:
		return 100

	@property
	def context_window(self) -> int:
		return 4096

	@property
	def generation_model(self) -> str:
		return self._generation_model

	@property
	def embedding_model(self) -> str:
		return self._embedding_model

	def generate(self, prompt: str) -> GenerationResult:
		return GenerationResult(text=f"{self._name}:{prompt}", model=self._generation_model, tokens_in=1, tokens_out=1, latency_ms=1)

	def embed(self, texts: List[str]) -> EmbeddingResult:
		return EmbeddingResult(vectors=[[1.0] * 3 for _ in texts], model=self._embedding_model)

	def count_tokens(self, text: str) -> int:
		return max(1, len(text))


def _build_policy(providers: Dict[str, BaseProvider]) -> RouterPolicy:
	return RouterPolicy(ProviderRegistry(providers))


def test_choose_provider_for_embedding_by_model() -> None:
	policy = _build_policy(
		{
			"openai": DummyProvider("openai", "text-embedding-3-small"),
			"mistral": DummyProvider("mistral", "mistral-embed"),
		}
	)
	provider = policy.choose_provider_for_embedding("text-embedding-3-small")
	assert provider.name == "openai"


def test_choose_provider_for_embedding_by_provider_name() -> None:
	policy = _build_policy(
		{
			"openai": DummyProvider("openai", "text-embedding-3-small"),
			"ollama": DummyProvider("ollama", "nomic-embed-text"),
		}
	)
	provider = policy.choose_provider_for_embedding("ollama")
	assert provider.name == "ollama"


def test_choose_provider_for_embedding_fallback() -> None:
	policy = _build_policy({"openai": DummyProvider("openai", "text-embedding-3-small")})
	provider = policy.choose_provider_for_embedding(None)
	assert provider.name == "openai"

