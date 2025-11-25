from __future__ import annotations

import os
import re
from typing import List, Sequence

from shared.contracts import SpanRef
from domain.schemas import QaRequest, QaResponse
from clients.model_adapter import llm_generate
from clients.retrieval_service import search_context_spans
from services.qa_utils import estimate_confidence

QA_PROMPT_REF = os.getenv("QA_PROMPT_REF", "key:demo.qa.v1")
QA_MODEL_HINT = os.getenv("QA_MODEL_HINT", "openai")
QA_TOP_K = int(os.getenv("QA_TOP_K", "5"))
QA_MAX_QUERY_LEN = int(os.getenv("QA_MAX_QUERY_LEN", "600"))

BANNED_PATTERNS = [
	re.compile(r"(?i)\bshutdown\b"),
	re.compile(r"(?i)\berase\b.{0,20}\bsystem\b"),
	re.compile(r"(?i)\bhack\b"),
]


class QaAgentService:
	def __init__(
		self,
		retrieval_fn=search_context_spans,
		llm_fn=llm_generate,
	):
		self._retrieval_fn = retrieval_fn
		self._llm_fn = llm_fn

	async def answer(self, request: QaRequest) -> QaResponse:
		query = self._policy_guard(request.query)
		retrieval = await self._retrieval_fn(
			context_id=request.context_id,
			query=query,
			top_k=QA_TOP_K,
		)
		results = retrieval.get("results") or []
		if not results:
			return QaResponse(
				conversation_id=request.conversation_id,
				answer="Xin lỗi, tôi không tìm thấy thông tin trong ngữ cảnh hiện có.",
				citations=[],
				confidence=0.35,
			)
		citations = _spans_from_results(results)
		context_block = _format_context(results)
		llm_resp = await self._llm_fn(
			prompt_ref=QA_PROMPT_REF,
			variables={
				"query": query,
				"context": context_block,
				"instructions": "Chỉ trả lời dựa vào ngữ cảnh. Nếu không đủ thông tin hãy nói 'Tôi không chắc'.",
			},
			language=request.language or "auto",
			task="qa",
			model_hint=QA_MODEL_HINT,
		)
		answer = str(llm_resp.get("output") or "").strip()
		if not answer:
			answer = "Tôi không chắc về câu trả lời dựa trên dữ liệu hiện có."
		confidence = estimate_confidence(results, answer)
		return QaResponse(
			conversation_id=request.conversation_id,
			answer=answer,
			citations=citations,
			confidence=confidence,
		)

	def _policy_guard(self, query: str) -> str:
		clean = (query or "").strip()
		if not clean:
			raise ValueError("query_required")
		if len(clean) > QA_MAX_QUERY_LEN:
			raise ValueError("query_too_long")
		for pattern in BANNED_PATTERNS:
			if pattern.search(clean):
				raise ValueError("query_rejected")
		return clean


def _format_context(results: Sequence[dict]) -> str:
	lines: List[str] = []
	for res in results:
		span = res.get("span") or {}
		seg_id = span.get("segment_id") or res.get("segment_id") or "unknown"
		snippet = (res.get("snippet") or res.get("text") or "").strip()
		lines.append(f"[seg:{seg_id}] {snippet}")
	return "\n".join(lines[:QA_TOP_K])


def _spans_from_results(results: Sequence[dict]) -> List[SpanRef]:
	citations: List[SpanRef] = []
	for item in results:
		span_payload = item.get("span")
		if span_payload:
			citations.append(SpanRef.model_validate(span_payload))
	return citations[:QA_TOP_K]


qa_agent_service = QaAgentService()