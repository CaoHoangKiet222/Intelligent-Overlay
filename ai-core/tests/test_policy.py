from typing import List
from providers.base import BaseProvider
from providers.registry import ProviderRegistry
from routing.policy import RouterPolicy, RoutingCriteria


class FakeProvider(BaseProvider):
	def __init__(self, name: str, cost: float, lat: int, ctx: int) -> None:
		self._name = name
		self._cost = cost
		self._lat = lat
		self._ctx = ctx

	@property
	def name(self) -> str:
		return self._name

	@property
	def cost_per_1k_tokens(self) -> float:
		return self._cost

	@property
	def latency_ms_estimate(self) -> int:
		return self._lat

	@property
	def context_window(self) -> int:
		return self._ctx

	def generate(self, prompt: str):
		class R:
			text = f"{self._name}:{prompt}"
		return R()

	def embed(self, texts: List[str]):
		class R:
			vectors = [[1.0] * 3 for _ in texts]
		return R()

	def count_tokens(self, text: str) -> int:
		return len(text)


def test_policy_selects_by_cost_then_latency():
	registry = ProviderRegistry({
		"a": FakeProvider("a", cost=0.8, lat=900, ctx=32_000),
		"b": FakeProvider("b", cost=0.3, lat=950, ctx=32_000),
	})
	policy = RouterPolicy(registry)
	crit = RoutingCriteria(cost_target=0.5, latency_target_ms=None, context_len=None, language=None, provider_hint=None)
	chosen = policy.choose_provider_for_generation(crit)
	assert chosen is not None
	assert chosen.name == "b"


def test_policy_respects_context_window():
	registry = ProviderRegistry({
		"a": FakeProvider("a", cost=0.2, lat=600, ctx=8_000),
		"b": FakeProvider("b", cost=0.5, lat=700, ctx=128_000),
	})
	policy = RouterPolicy(registry)
	crit = RoutingCriteria(cost_target=None, latency_target_ms=None, context_len=100_000, language=None, provider_hint=None)
	chosen = policy.choose_provider_for_generation(crit)
	assert chosen is not None
	assert chosen.name == "b"


def test_policy_uses_hint():
	registry = ProviderRegistry({
		"a": FakeProvider("a", cost=0.2, lat=600, ctx=8_000),
		"b": FakeProvider("b", cost=0.5, lat=700, ctx=128_000),
	})
	policy = RouterPolicy(registry)
	crit = RoutingCriteria(cost_target=None, latency_target_ms=None, context_len=None, language=None, provider_hint="a")
	chosen = policy.choose_provider_for_generation(crit)
	assert chosen is not None and chosen.name == "a"


