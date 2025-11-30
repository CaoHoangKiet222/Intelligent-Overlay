from __future__ import annotations

import time
from typing import List

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

import io
import time

from domain.errors import ProviderCallError
from domain.models import EmbeddingResult, GenerationResult, TranscriptionResult, TranscriptSegment, OCRResult
from providers.base import BaseProvider
from providers.mock_embeddings import build_mock_embeddings, DEFAULT_MOCK_EMBED_DIM
from providers.mock_generation import generate_mock_output

CHAT_COMPLETIONS_ENDPOINT = "/chat/completions"
EMBEDDINGS_ENDPOINT = "/embeddings"
TRANSCRIPTIONS_ENDPOINT = "/audio/transcriptions"
DEFAULT_CHAT_MODEL = "gpt-4o-mini"
DEFAULT_EMBED_MODEL = "text-embedding-3-small"
DEFAULT_VISION_MODEL = "gpt-4o"


class OpenAIProvider(BaseProvider):
	def __init__(self, api_key: str, chat_model: str = DEFAULT_CHAT_MODEL, embedding_model: str = DEFAULT_EMBED_MODEL) -> None:
		self._api_key = (api_key or "").strip()
		self._chat_model = chat_model
		self._embedding_model = embedding_model
		self._mock_mode = not bool(self._api_key)
		self._client: httpx.Client | None = None
		if not self._mock_mode:
			from shared.config.base import get_base_config
			timeout_config = get_base_config().timeout_config
			timeout = timeout_config.providers.get_openai_timeout()
			self._client = httpx.Client(
				base_url="https://api.openai.com/v1",
				timeout=timeout,
				headers={
					"Authorization": f"Bearer {self._api_key}",
					"Content-Type": "application/json",
				},
			)

	@property
	def name(self) -> str:
		return "openai"

	@property
	def cost_per_1k_tokens(self) -> float:
		return 0.5

	@property
	def latency_ms_estimate(self) -> int:
		return 800

	@property
	def context_window(self) -> int:
		return 128000

	@property
	def generation_model(self) -> str:
		return self._chat_model

	@property
	def embedding_model(self) -> str:
		return self._embedding_model

	def generate(self, prompt: str) -> GenerationResult:
		start = time.perf_counter()
		if self._mock_mode:
			return self._mock_generation(prompt, start)

		client = self._ensure_client()
		payload = {
			"model": self._chat_model,
			"messages": [{"role": "user", "content": prompt}],
			"temperature": 0.2,
		}
		try:
			response = self._post_with_retry(client, CHAT_COMPLETIONS_ENDPOINT, payload)
		except httpx.HTTPError as exc:
			raise ProviderCallError(f"openai chat error: {exc}") from exc

		data = response.json()
		choices = data.get("choices") or []
		if not choices:
			raise ProviderCallError("openai chat error: empty choices")

		message = choices[0].get("message") or {}
		content = message.get("content", "")
		if isinstance(content, list):
			content = "".join(part.get("text", "") for part in content if isinstance(part, dict))

		usage = data.get("usage") or {}
		latency_ms = int((time.perf_counter() - start) * 1000)
		return GenerationResult(
			text=str(content),
			model=str(data.get("model") or self._chat_model),
			tokens_in=usage.get("prompt_tokens"),
			tokens_out=usage.get("completion_tokens"),
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
			raise ProviderCallError(f"openai embed error: {exc}") from exc

		data = response.json()
		vectors = [entry.get("embedding", []) for entry in data.get("data", [])]
		if len(vectors) != len(texts):
			raise ProviderCallError("openai embed error: mismatched vector count")

		float_vectors = [list(map(float, vec)) for vec in vectors]
		dim = len(float_vectors[0]) if float_vectors else 0
		return EmbeddingResult(vectors=float_vectors, model=str(data.get("model") or self._embedding_model), dim=dim)

	def count_tokens(self, text: str) -> int:
		return max(1, len(text) // 4)

	def transcribe(self, audio_bytes: bytes, lang_hint: str | None = None) -> TranscriptionResult:
		start = time.perf_counter()
		if self._mock_mode:
			return TranscriptionResult(
				segments=[
					TranscriptSegment(
						text="[STT_MOCK: OpenAI API key not configured]",
						start_ms=0,
						end_ms=1000,
						speaker_label=None
					)
				],
				model="whisper-1",
				latency_ms=int((time.perf_counter() - start) * 1000),
			)

		client = self._ensure_client()
		files = {
			"file": ("audio", io.BytesIO(audio_bytes), "audio/mpeg")
		}
		data: dict[str, str] = {
			"model": "whisper-1",
			"response_format": "verbose_json",
		}
		if lang_hint:
			lang_code = lang_hint.split("-")[0] if "-" in lang_hint else lang_hint
			data["language"] = lang_code

		try:
			response = client.post(TRANSCRIPTIONS_ENDPOINT, files=files, data=data)
			response.raise_for_status()
			result = response.json()

			text = result.get("text", "")
			segments_raw = result.get("segments", [])

			if segments_raw:
				transcript_segments = []
				for seg in segments_raw:
					transcript_segments.append(
						TranscriptSegment(
							text=seg.get("text", "").strip(),
							start_ms=int(seg.get("start", 0) * 1000),
							end_ms=int(seg.get("end", 0) * 1000),
							speaker_label=None
						)
					)
				segments = transcript_segments
			else:
				segments = [
					TranscriptSegment(
						text=text,
						start_ms=0,
						end_ms=0,
						speaker_label=None
					)
				]

			latency_ms = int((time.perf_counter() - start) * 1000)
			return TranscriptionResult(
				segments=segments,
				model="whisper-1",
				latency_ms=latency_ms,
			)
		except httpx.HTTPError as exc:
			raise ProviderCallError(f"openai transcribe error: {exc}") from exc

	def extract_text_from_image(self, image_data_base64: str, lang_hint: str | None = None) -> OCRResult:
		start = time.perf_counter()
		if self._mock_mode:
			return OCRResult(
				text="[OCR_MOCK: OpenAI API key not configured]",
				model=DEFAULT_VISION_MODEL,
				latency_ms=int((time.perf_counter() - start) * 1000),
			)

		client = self._ensure_client()
		image_url = f"data:image/jpeg;base64,{image_data_base64}"

		prompt = "Extract all text from this image. Preserve the structure and formatting as much as possible. If the image contains multiple languages, extract text in all languages."
		if lang_hint:
			lang_name = {"vi": "Vietnamese", "en": "English", "zh": "Chinese", "ja": "Japanese", "ko": "Korean"}.get(lang_hint.lower(), "")
			if lang_name:
				prompt += f" Pay special attention to {lang_name} text."

		payload = {
			"model": DEFAULT_VISION_MODEL,
			"messages": [
				{
					"role": "user",
					"content": [
						{
							"type": "text",
							"text": prompt
						},
						{
							"type": "image_url",
							"image_url": {
								"url": image_url
							}
						}
					]
				}
			],
			"max_tokens": 4096,
			"temperature": 0.1,
		}

		try:
			response = self._post_with_retry(client, CHAT_COMPLETIONS_ENDPOINT, payload)
			data = response.json()

			choices = data.get("choices", [])
			if not choices:
				raise ProviderCallError("openai ocr error: empty choices")

			message = choices[0].get("message", {})
			content = message.get("content", "")

			if not content:
				raise ProviderCallError("openai ocr error: no text extracted")

			latency_ms = int((time.perf_counter() - start) * 1000)
			return OCRResult(
				text=content.strip(),
				model=DEFAULT_VISION_MODEL,
				latency_ms=latency_ms,
			)
		except httpx.HTTPError as exc:
			raise ProviderCallError(f"openai ocr error: {exc}") from exc

	def _mock_generation(self, prompt: str, start: float) -> GenerationResult:
		text = generate_mock_output(self.name, prompt)
		return GenerationResult(
			text=text,
			model=self._chat_model,
			tokens_in=self.count_tokens(prompt),
			tokens_out=self.count_tokens(text),
			latency_ms=int((time.perf_counter() - start) * 1000),
		)

	def _ensure_client(self) -> httpx.Client:
		if self._client is None:
			raise ProviderCallError("openai client is not initialized")
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
