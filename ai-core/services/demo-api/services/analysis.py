from __future__ import annotations

import asyncio
import re
from typing import Dict, List, Tuple
from domain.schemas import (
	AnalysisBundle,
	ContextBundle,
	ContextChunk,
	SummaryBullet,
	ArgumentEntry,
	ImplicationItem,
	SentimentResult,
	LogicBiasIssue,
	SpanRef,
)
from clients.model_adapter import ModelAdapterClient
from metrics.prometheus import worker_counter
from services.prompt_bootstrap import PromptProvider

SEG_PATTERN = re.compile(r"seg:([0-9a-fA-F\-]{8,})", re.IGNORECASE)


class AnalysisService:
	def __init__(self, prompt_provider: PromptProvider, model_client: ModelAdapterClient, prompt_keys: Dict[str, str], provider_hint: str):
		self._prompt_provider = prompt_provider
		self._model_client = model_client
		self._prompt_keys = prompt_keys
		self._provider_hint = provider_hint

	async def run(self, bundle: ContextBundle) -> AnalysisBundle:
		self._ensure_segments(bundle)
		context_text, lookup = _build_context(bundle.segments)

		tasks = [
			asyncio.create_task(self._run_summary(bundle, context_text, lookup)),
			asyncio.create_task(self._run_argument(bundle, context_text, lookup)),
			asyncio.create_task(self._run_implication(bundle, context_text, lookup)),
			asyncio.create_task(self._run_logic_bias(bundle, context_text, lookup)),
		]
		summary, arguments, (implications, sentiment), logic_bias = await asyncio.gather(*tasks)

		return AnalysisBundle(
			context_id=bundle.context_id,
			summary=summary,
			arguments=arguments,
			implications=implications,
			sentiment=sentiment,
			logic_bias=logic_bias,
		)

	def _ensure_segments(self, bundle: ContextBundle) -> None:
		if bundle.segments:
			return
		fallback = ContextChunk(
			segment_id=f"{bundle.context_id}-fallback",
			text=bundle.raw_text[:400],
			start_offset=0,
			end_offset=min(len(bundle.raw_text), 400),
		)
		bundle.segments = [fallback]
		bundle.rebuild_index()

	async def _call_worker(self, worker: str, prompt_key: str, variables: Dict[str, str], language: str | None) -> str:
		prompt = await self._prompt_provider.render(prompt_key, **variables)
		worker_counter.labels(worker=worker).inc()
		resp = await self._model_client.generate(prompt, language=language, provider_hint=self._provider_hint)
		return resp.get("output", "")

	async def _run_summary(self, bundle: ContextBundle, context_text: str, lookup: Dict[str, ContextChunk]) -> List[SummaryBullet]:
		output = await self._call_worker("summary", self._prompt_keys["summary"], {"context": context_text}, bundle.locale)
		lines = [line.strip("-• ").strip() for line in output.splitlines() if line.strip().startswith(("-", "•"))]
		if not lines:
			lines = [bundle.raw_text.strip()[:160]]
		return [
			SummaryBullet(text=line, citations=_make_span_refs(_extract_segment_ids(line), lookup, fallback_index=idx))
			for idx, line in enumerate(lines[:5])
		]

	async def _run_argument(self, bundle: ContextBundle, context_text: str, lookup: Dict[str, ContextChunk]) -> List[ArgumentEntry]:
		output = await self._call_worker("argument", self._prompt_keys["argument"], {"context": context_text}, bundle.locale)
		claim, evidence, reasoning = _parse_labeled_block(output)
		return [
			ArgumentEntry(
				claim=claim,
				evidence=_make_span_refs(_extract_segment_ids(evidence), lookup, fallback_index=0),
				reasoning=reasoning,
				confidence=0.72,
			)
		]

	async def _run_implication(self, bundle: ContextBundle, context_text: str, lookup: Dict[str, ContextChunk]) -> Tuple[List[ImplicationItem], SentimentResult]:
		output = await self._call_worker("implication", self._prompt_keys["implication"], {"context": context_text}, bundle.locale)
		implications, sentiment_line = _parse_implication_block(output)
		items = [
			ImplicationItem(text=text, citations=_make_span_refs(_extract_segment_ids(text), lookup, fallback_index=idx))
			for idx, text in enumerate(implications)
		]
		label, explanation = _parse_sentiment(sentiment_line)
		sentiment = SentimentResult(
			label=label,
			explanation=explanation,
			citations=_make_span_refs(_extract_segment_ids(explanation), lookup, fallback_index=0),
		)
		return items, sentiment

	async def _run_logic_bias(self, bundle: ContextBundle, context_text: str, lookup: Dict[str, ContextChunk]) -> List[LogicBiasIssue]:
		output = await self._call_worker("logic_bias", self._prompt_keys["logic_bias"], {"context": context_text}, bundle.locale)
		issues = []
		for line in output.splitlines():
			line = line.strip()
			if not line or "ISSUE" not in line:
				continue
			issue = _parse_logic_bias_line(line)
			if not issue:
				continue
			segment_ids = _extract_segment_ids(issue["segment"])
			severity = issue["severity"]
			issues.append(
				LogicBiasIssue(
					type=issue["issue_type"],
					severity=severity,
					explanation=issue["note"],
					citations=_make_span_refs(segment_ids, lookup, fallback_index=0),
				)
			)
		if not issues:
			issues.append(
				LogicBiasIssue(
					type="no_issue_detected",
					severity=1,
					explanation="Không phát hiện lỗi rõ ràng dựa trên ngữ cảnh giới hạn.",
					citations=_make_span_refs([], lookup, fallback_index=0),
				)
			)
		return issues


def _build_context(segments: List[ContextChunk]) -> Tuple[str, Dict[str, ContextChunk]]:
	lookup = {seg.chunk_id.lower(): seg for seg in segments}
	text = "\n".join(f"[seg:{seg.chunk_id.lower()}] {seg.text}" for seg in segments)
	return text, lookup


def _extract_segment_ids(text: str) -> List[str]:
	return [match.lower() for match in SEG_PATTERN.findall(text)]


def _make_span_refs(segment_ids: List[str], lookup: Dict[str, ContextChunk], fallback_index: int) -> List[SpanRef]:
	if not segment_ids:
		return [_fallback_span(list(lookup.values()), fallback_index)]
	refs = []
	for seg_id in segment_ids:
		seg = lookup.get(seg_id)
		if seg:
			refs.append(_to_span(seg))
	if refs:
		return refs
	return [_fallback_span(list(lookup.values()), fallback_index)]


def _fallback_span(segments: List[ContextChunk], fallback_index: int) -> SpanRef:
	if not segments:
		return SpanRef(chunk_id="unknown", text_preview=None)
	seg = segments[min(fallback_index, len(segments) - 1)]
	return _to_span(seg)


def _to_span(seg: ContextChunk) -> SpanRef:
	return SpanRef(
		chunk_id=seg.chunk_id,
		start_offset=seg.start_offset,
		end_offset=seg.end_offset,
		text_preview=seg.text[:160],
	)


def _parse_labeled_block(block: str) -> Tuple[str, str, str]:
	lines = block.splitlines()
	claim = ""
	evidence = ""
	reasoning = ""
	for line in lines:
		upper = line.upper()
		if upper.startswith("CLAIM:"):
			claim = line.split(":", 1)[1].strip()
		elif upper.startswith("EVIDENCE:"):
			evidence = line.split(":", 1)[1].strip()
		elif upper.startswith("REASONING:"):
			reasoning = line.split(":", 1)[1].strip()
	return claim or "Không trích xuất được luận điểm chính.", evidence or claim, reasoning or claim


def _parse_implication_block(text: str) -> Tuple[List[str], str]:
	lines = [line.strip() for line in text.splitlines() if line.strip()]
	implications: List[str] = []
	sentiment_line = ""
	for line in lines:
		if line.upper().startswith("SENTIMENT"):
			sentiment_line = line
			continue
		if line[0].isdigit() and "." in line:
			implications.append(line.split(".", 1)[1].strip())
		elif line.startswith("-"):
			implications.append(line[1:].strip())
	return implications[:2] or ["Không trích xuất được hàm ý."], sentiment_line or "SENTIMENT: neutral - Không rõ cảm xúc."


def _parse_sentiment(line: str) -> Tuple[str, str]:
	if ":" not in line:
		return "neutral", line or ""
	_, rest = line.split(":", 1)
	parts = rest.split("-", 1)
	label = parts[0].strip().lower()
	if label not in {"positive", "negative", "neutral", "mixed"}:
		label = "neutral"
	explanation = parts[1].strip() if len(parts) > 1 else rest.strip()
	return label, explanation or "Không có giải thích chi tiết."


def _parse_logic_bias_line(line: str) -> Dict[str, str] | None:
	chunks = [chunk.strip() for chunk in line.split(";") if chunk.strip()]
	payload: Dict[str, str] = {}
	for chunk in chunks:
		if ":" not in chunk:
			continue
		key, value = chunk.split(":", 1)
		payload[key.strip().lower()] = value.strip()
	try:
		return {
			"issue_type": payload.get("issue", "unspecified"),
			"segment": payload.get("seg", ""),
			"severity": max(1, min(3, int(payload.get("severity", "1")))),
			"note": payload.get("note", ""),
		}
	except ValueError:
		return None

