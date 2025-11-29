from __future__ import annotations

import time
import os
from typing import List

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from domain.errors import ProviderCallError
from domain.models import EmbeddingResult, GenerationResult
from providers.base import BaseProvider
from providers.mock_embeddings import build_mock_embeddings, DEFAULT_MOCK_EMBED_DIM
from providers.mock_generation import generate_mock_output

CHAT_COMPLETIONS_ENDPOINT = "/chat"
EMBEDDINGS_ENDPOINT = "/embed"
DEFAULT_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434/api")
DEFAULT_GENERATION_MODEL = "phi3:mini"
DEFAULT_EMBED_MODEL = "qwen3-embedding:0.6b"


class OllamaProvider(BaseProvider):
	def __init__(self, api_key: str = "ollama", base_url: str = DEFAULT_BASE_URL, generation_model: str = DEFAULT_GENERATION_MODEL, embedding_model: str = DEFAULT_EMBED_MODEL) -> None:
		self._api_key = (api_key or "ollama").strip()
		self._base_url = base_url.rstrip("/")
		self._generation_model = generation_model
		self._embedding_model = embedding_model
		self._mock_mode = False
		self._client: httpx.Client | None = None
		if not self._mock_mode:
			self._client = httpx.Client(
				base_url=self._base_url,
				timeout=httpx.Timeout(120.0, connect=30.0),
				headers={
					"Authorization": f"Bearer {self._api_key}",
					"Content-Type": "application/json",
				},
			)

	@property
	def name(self) -> str:
		return "ollama"

	@property
	def cost_per_1k_tokens(self) -> float:
		return 0.0

	@property
	def latency_ms_estimate(self) -> int:
		return 500

	@property
	def context_window(self) -> int:
		return 8192

	@property
	def generation_model(self) -> str:
		return self._generation_model

	@property
	def embedding_model(self) -> str:
		return self._embedding_model

	def generate(self, prompt: str) -> GenerationResult:
		start = time.perf_counter()
		if self._mock_mode:
			return self._mock_generation(prompt, start)

		client = self._ensure_client()
		payload = {
			"model": self._generation_model,
			"messages": [{"role": "user", "content": prompt}],
			"temperature": 0.2,
		}
		try:
			response = self._post_with_retry(client, CHAT_COMPLETIONS_ENDPOINT, payload)
		except httpx.HTTPError as exc:
			raise ProviderCallError(f"ollama chat error: {exc}") from exc

		data = response.json()
		choices = data.get("choices") or []
		if not choices:
			raise ProviderCallError("ollama chat error: empty choices")

		message = choices[0].get("message") or {}
		content = message.get("content", "")
		if isinstance(content, list):
			content = "".join(part.get("text", "") for part in content if isinstance(part, dict))

		usage = data.get("usage") or {}
		latency_ms = int((time.perf_counter() - start) * 1000)
		return GenerationResult(
			text=str(content),
			model=str(data.get("model") or self._generation_model),
			tokens_in=usage.get("prompt_tokens") or self.count_tokens(prompt),
			tokens_out=usage.get("completion_tokens") or self.count_tokens(str(content)),
			latency_ms=latency_ms,
		)

	def embed(self, texts: List[str]) -> EmbeddingResult:
		if self._mock_mode:
			mock_vectors = build_mock_embeddings(texts)
			return EmbeddingResult(
				vectors=mock_vectors,
				model=self._embedding_model,
				dim=DEFAULT_MOCK_EMBED_DIM if mock_vectors else 0,
			)

		client = self._ensure_client()
		payload = {"model": self._embedding_model, "input": texts}
		try:
			response = self._post_with_retry(client, EMBEDDINGS_ENDPOINT, payload)
		except httpx.HTTPError as exc:
			raise ProviderCallError(f"ollama embed error: {exc}") from exc

		data = response.json()
		vectors = [entry.get("embedding", []) for entry in data.get("data", [])]
		if len(vectors) != len(texts):
			raise ProviderCallError("ollama embed error: mismatched vector count")

		float_vectors = [list(map(float, vec)) for vec in vectors]
		dim = len(float_vectors[0]) if float_vectors else 0
		return EmbeddingResult(vectors=float_vectors, model=str(data.get("model") or self._embedding_model), dim=dim)

	def count_tokens(self, text: str) -> int:
		return max(1, len(text) // 4)

	def _mock_generation(self, prompt: str, start: float) -> GenerationResult:
		text = generate_mock_output(self.name, prompt)
		return GenerationResult(
			text=text,
			model=self._generation_model,
			tokens_in=self.count_tokens(prompt),
			tokens_out=self.count_tokens(text),
			latency_ms=int((time.perf_counter() - start) * 1000),
		)

	def _ensure_client(self) -> httpx.Client:
		if self._client is None:
			raise ProviderCallError("ollama client is not initialized")
		return self._client

	@staticmethod
	@retry(
		stop=stop_after_attempt(3),
		wait=wait_exponential(min=0.5, max=4),
		retry=retry_if_exception_type(httpx.HTTPError),
	)
	def _post_with_retry(client: httpx.Client, endpoint: str, payload: dict) -> httpx.Response:
		response = client.post(endpoint, json=payload)
		if response.status_code in (429, 500, 502, 503, 504):
			raise httpx.HTTPStatusError("retryable error", request=response.request, response=response)
		response.raise_for_status()
		return response
