from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from providers.base import BaseProvider
from providers.registry import ProviderRegistry


@dataclass(frozen=True)
class RoutingCriteria:
	cost_target: Optional[float]
	latency_target_ms: Optional[int]
	context_len: Optional[int]
	language: Optional[str]
	provider_hint: Optional[str]


class RouterPolicy:
	def __init__(self, registry: ProviderRegistry, task_routing: Optional[dict[str, str]] = None) -> None:
		self._registry = registry
		self._task_routing = {k.lower(): v for k, v in (task_routing or {}).items()}

	def default_embedding_provider(self) -> str:
		return "openai" if "openai" in self._registry.names() else self._registry.names()[0]

	def choose_provider_for_embedding(self, model_hint: Optional[str]) -> BaseProvider:
		if model_hint:
			if model_hint in self._registry.names():
				return self._registry.get(model_hint)
			lowered = model_hint.lower()
			for name in self._registry.names():
				provider = self._registry.get(name)
				if provider.embedding_model.lower() == lowered:
					return provider
		return self._registry.get(self.default_embedding_provider())

	def choose_provider_for_task(self, task: str, criteria: RoutingCriteria) -> Optional[BaseProvider]:
		task_hint = self._task_routing.get(task.lower())
		if task_hint:
			try:
				return self._registry.get(task_hint)
			except KeyError:
				pass
		return self.choose_provider_for_generation(criteria)

	def choose_provider_for_generation(self, criteria: RoutingCriteria) -> Optional[BaseProvider]:
		if criteria.provider_hint:
			return self._registry.get(criteria.provider_hint)

		candidates = [self._registry.get(n) for n in self._registry.names()]

		if criteria.context_len is not None:
			candidates = [p for p in candidates if p.context_window >= criteria.context_len]
			if not candidates:
				return None

		if criteria.cost_target is not None:
			candidates = sorted(candidates, key=lambda p: p.cost_per_1k_tokens)
			candidates = [p for p in candidates if p.cost_per_1k_tokens <= criteria.cost_target] or candidates

		if criteria.latency_target_ms is not None:
			candidates = sorted(candidates, key=lambda p: p.latency_ms_estimate)
			candidates = [p for p in candidates if p.latency_ms_estimate <= criteria.latency_target_ms] or candidates

		if criteria.language:
			if criteria.language.lower().startswith("vi"):
				candidates = sorted(candidates, key=lambda p: p.cost_per_1k_tokens)
			else:
				candidates = sorted(candidates, key=lambda p: p.latency_ms_estimate)

		return candidates[0] if candidates else None


