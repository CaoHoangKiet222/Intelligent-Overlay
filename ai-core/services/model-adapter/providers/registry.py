from __future__ import annotations
from typing import Dict, List
from providers.base import BaseProvider
from app.config import AppConfig
from providers.openai_provider import OpenAIProvider
from providers.anthropic_provider import AnthropicProvider
from providers.mistral_provider import MistralProvider
from providers.ollama_provider import OllamaProvider


class ProviderRegistry:
	def __init__(self, providers: Dict[str, BaseProvider]) -> None:
		self._providers = providers

	@staticmethod
	def from_config(cfg: AppConfig) -> "ProviderRegistry":
		providers: Dict[str, BaseProvider] = {}
		providers["openai"] = OpenAIProvider(cfg.provider_keys.get("openai", ""))
		providers["anthropic"] = AnthropicProvider(cfg.provider_keys.get("anthropic", ""))
		providers["mistral"] = MistralProvider(cfg.provider_keys.get("mistral", ""))
		providers["ollama"] = OllamaProvider(cfg.provider_keys.get("ollama", ""))
		return ProviderRegistry(providers)

	def get(self, name: str) -> BaseProvider:
		return self._providers[name]

	def names(self) -> List[str]:
		return list(self._providers.keys())

	def list_providers_summary(self) -> Dict[str, Dict[str, str | int | float]]:
		summary: Dict[str, Dict[str, str | int | float]] = {}
		for name, provider in self._providers.items():
			summary[name] = {
				"name": provider.name,
				"cost_per_1k_tokens": provider.cost_per_1k_tokens,
				"latency_ms_estimate": provider.latency_ms_estimate,
				"context_window": provider.context_window,
			}
		return summary


