from __future__ import annotations
from typing import List
from providers.registry import ProviderRegistry
from routing.policy import RouterPolicy
from shared.telemetry.decorators import llm_usage


class GenerationService:
	def __init__(self, registry: ProviderRegistry, policy: RouterPolicy) -> None:
		self._registry = registry
		self._policy = policy

	def generate(self, provider_name: str, prompt: str) -> str:
		provider = self._registry.get(provider_name)
		result = provider.generate(prompt)
		# Providers mock không trả tokens/model; metric tối thiểu với 0 tokens
		llm_usage(provider=provider.name, model="", tokens_in=0, tokens_out=0, latency_ms=0)
		return result.text

	def embed(self, provider_name: str, texts: List[str]) -> List[List[float]]:
		provider = self._registry.get(provider_name)
		return provider.embed(texts).vectors


