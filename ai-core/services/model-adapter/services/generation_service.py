from __future__ import annotations
import time
from typing import List
from domain.models import EmbeddingResult, GenerationResult
from providers.registry import ProviderRegistry
from routing.policy import RouterPolicy
from shared.telemetry.decorators import llm_usage


class GenerationService:
	def __init__(self, registry: ProviderRegistry, policy: RouterPolicy) -> None:
		self._registry = registry
		self._policy = policy

	def generate(self, provider_name: str, prompt: str) -> str:
		provider = self._registry.get(provider_name)
		start = time.perf_counter()
		result = provider.generate(prompt)
		latency_ms = result.latency_ms if result.latency_ms is not None else int((time.perf_counter() - start) * 1000)
		tokens_in = result.tokens_in if result.tokens_in is not None else provider.count_tokens(prompt)
		tokens_out = result.tokens_out if result.tokens_out is not None else provider.count_tokens(result.text)
		model_name = result.model or provider.generation_model
		llm_usage(provider=provider.name, model=model_name, tokens_in=tokens_in, tokens_out=tokens_out, latency_ms=latency_ms)
		return result.text

	def embed(self, provider_name: str, texts: List[str]) -> EmbeddingResult:
		provider = self._registry.get(provider_name)
		return provider.embed(texts)


