from __future__ import annotations
from typing import List
from providers.registry import ProviderRegistry
from routing.policy import RouterPolicy


class GenerationService:
	def __init__(self, registry: ProviderRegistry, policy: RouterPolicy) -> None:
		self._registry = registry
		self._policy = policy

	def generate(self, provider_name: str, prompt: str) -> str:
		provider = self._registry.get(provider_name)
		return provider.generate(prompt).text

	def embed(self, provider_name: str, texts: List[str]) -> List[List[float]]:
		provider = self._registry.get(provider_name)
		return provider.embed(texts).vectors


