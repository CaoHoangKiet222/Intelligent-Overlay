from __future__ import annotations

import re
from typing import Dict, List, Tuple, Any
from domain.schemas import DemoQAResponse, SpanRef
from clients.retrieval import RetrievalClient
from clients.model_adapter import ModelAdapterClient
from services.prompt_bootstrap import PromptProvider
from services.analysis import SEG_PATTERN
from metrics.prometheus import worker_counter


class QAService:
	def __init__(self, retrieval_client: RetrievalClient, prompt_provider: PromptProvider, model_client: ModelAdapterClient,
	             qa_prompt_key: str, provider_hint: str, top_k: int = 4):
		self._retrieval = retrieval_client
		self._prompt_provider = prompt_provider
		self._model_client = model_client
		self._qa_prompt_key = qa_prompt_key
		self._provider_hint = provider_hint
		self._top_k = top_k

	async def answer(self, context_id: str, query: str, locale: str | None) -> DemoQAResponse:
		search = await self._retrieval.search(context_id=context_id, query=query, top_k=self._top_k)
		context_text, lookup = _build_context_from_results(search.get("results") or [])
		if not lookup:
			return DemoQAResponse(answer="Không tìm thấy dữ liệu phù hợp để trả lời.", citations=[], confidence=0.0)

		prompt = await self._prompt_provider.render(self._qa_prompt_key, context=context_text, question=query)
		worker_counter.labels(worker="qa").inc()
		resp = await self._model_client.generate(prompt, language=locale, provider_hint=self._provider_hint)
		answer, citation_ids, confidence = _parse_qa_output(resp.get("output", ""))
		citations = _spans_from_ids(citation_ids, lookup)
		return DemoQAResponse(answer=answer, citations=citations, confidence=confidence)


def _build_context_from_results(results: List[Dict[str, Any]]) -> Tuple[str, Dict[str, SpanRef]]:
	lookup: Dict[str, SpanRef] = {}
	chunks: List[str] = []
	for item in results:
		span_payload = item.get("span") or {}
		if "segment_id" not in span_payload:
			continue
		span = SpanRef(**span_payload)
		seg_id = span.chunk_id.lower()
		snippet = item.get("snippet") or span.text_preview or ""
		score = float(item.get("score") or span.score or 0.0)
		span.score = score
		if not span.text_preview:
			span.text_preview = snippet[:200]
		chunks.append(f"[seg:{seg_id}] {snippet}")
		lookup[seg_id] = span
	return "\n".join(chunks), lookup


def _parse_qa_output(output: str) -> Tuple[str, List[str], float]:
	answer = ""
	confidence = 0.6
	citation_ids: List[str] = []
	for line in output.splitlines():
		if line.upper().startswith("ANSWER:"):
			answer = line.split(":", 1)[1].strip()
		elif line.upper().startswith("CITATIONS:"):
			citation_ids = [token.strip().lower() for token in SEG_PATTERN.findall(line)]
		elif line.upper().startswith("CONFIDENCE:"):
			confidence = _safe_confidence(line.split(":", 1)[1].strip())
	if not answer:
		answer = output.strip() or "Không thể tạo câu trả lời."
	return answer, citation_ids, round(confidence, 2)


def _safe_confidence(raw: str) -> float:
	try:
		value = float(re.sub(r"[^\d\.]", "", raw))
		return max(0.0, min(1.0, value))
	except ValueError:
		return 0.6


def _spans_from_ids(ids: List[str], lookup: Dict[str, SpanRef]) -> List[SpanRef]:
	unique_ids = []
	for seg_id in ids:
		if seg_id not in unique_ids:
			unique_ids.append(seg_id)
	result = [lookup[seg_id] for seg_id in unique_ids if seg_id in lookup]
	if result:
		return result
	return list(lookup.values())[:1]

