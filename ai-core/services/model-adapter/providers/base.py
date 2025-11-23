from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List
from domain.models import GenerationResult, EmbeddingResult


class BaseProvider(ABC):
	@property
	@abstractmethod
	def name(self) -> str:
		raise NotImplementedError

	@property
	@abstractmethod
	def cost_per_1k_tokens(self) -> float:
		raise NotImplementedError

	@property
	@abstractmethod
	def latency_ms_estimate(self) -> int:
		raise NotImplementedError

	@property
	@abstractmethod
	def context_window(self) -> int:
		raise NotImplementedError

	@property
	@abstractmethod
	def generation_model(self) -> str:
		raise NotImplementedError

	@property
	@abstractmethod
	def embedding_model(self) -> str:
		raise NotImplementedError

	@abstractmethod
	def generate(self, prompt: str) -> GenerationResult:
		raise NotImplementedError

	@abstractmethod
	def embed(self, texts: List[str]) -> EmbeddingResult:
		raise NotImplementedError

	@abstractmethod
	def count_tokens(self, text: str) -> int:
		raise NotImplementedError


