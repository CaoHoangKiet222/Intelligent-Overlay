from __future__ import annotations

import asyncio
import json
import os
import re
from typing import Dict, List, Sequence, Tuple, Union

import ray
from shared.contracts import ContextChunk, SpanRef
from domain.schemas import (
	ImplicationItem,
	ImplicationSentimentOutput,
	SentimentResult,
)
from workers.base import call_llm_generate
from workers.utils import ensure_context_id, fetch_context_chunks, format_context, normalize_chunks

IMPLICATION_PROMPT_REF = os.getenv("IMPLICATION_PROMPT_REF", "key:demo.implication.v1")
SENTIMENT_PROMPT_REF = os.getenv("SENTIMENT_PROMPT_REF", "key:demo.sentiment.v1")
IMPLICATION_MODEL_HINT = os.getenv("IMPLICATION_MODEL_HINT", "openai")
SENTIMENT_MODEL_HINT = os.getenv("SENTIMENT_MODEL_HINT", "openai")
SENTIMENT_SEGMENT_LIMIT = int(os.getenv("SENTIMENT_SEGMENT_LIMIT", "12"))
MAX_IMPLICATIONS = int(os.getenv("MAX_IMPLICATIONS", "4"))
SEG_PATTERN = re.compile(r"seg:([0-9a-fA-F\-]{8,})", re.IGNORECASE)
SEG_MARKER = re.compile(r"\[seg:[0-9a-fA-F\-]{8,}\]", re.IGNORECASE)


async def analyze_implication_sentiment(
	context_id: str,
	*,
	language: str = "auto",
	segments: Sequence[Union[ContextChunk, Dict[str, object]]] | None = None,
	implication_prompt_ref: str | None = None,
	sentiment_prompt_ref: str | None = None,
) -> Tuple[ImplicationSentimentOutput, Dict[str, object]]:
	normalized_segments = normalize_chunks(segments or [])
	effective_context_id = ensure_context_id(context_id, normalized_segments)
	final_segments = normalized_segments or await fetch_context_chunks(effective_context_id, SENTIMENT_SEGMENT_LIMIT)
	context_text = format_context(final_segments)

	sentiment, sentiment_llm = await _classify_sentiment(
		context_text=context_text,
		prompt_ref=sentiment_prompt_ref or SENTIMENT_PROMPT_REF,
		language=language,
	)
	implications, implication_llm = await _generate_implications(
		context_text=context_text,
		chunks=final_segments,
		prompt_ref=implication_prompt_ref or IMPLICATION_PROMPT_REF,
		language=language,
	)
	payload = ImplicationSentimentOutput(
		context_id=effective_context_id,
		implications=implications,
		sentiment=sentiment,
	)
	return payload, implication_llm or sentiment_llm


async def _classify_sentiment(context_text: str, prompt_ref: str, language: str) -> Tuple[SentimentResult, Dict[str, object]]:
	resp = await call_llm_generate(
		task="sentiment",
		prompt_ref=prompt_ref,
		variables={"context": context_text},
		language=language or "auto",
		provider_hint=SENTIMENT_MODEL_HINT,
	)
	raw = str(resp.get("output") or "").strip()
	return _parse_sentiment_output(raw), resp


def _parse_sentiment_output(raw: str) -> SentimentResult:
	data: Dict[str, object] | None = None
	try:
		data = json.loads(raw)
	except json.JSONDecodeError:
		pass
	if not data:
		data = _fallback_parse(raw)
	label = _normalize_label(str(data.get("label") or data.get("sentiment") or "neutral"))
	score = float(data.get("score") or data.get("confidence") or 0.5)
	score = max(0.0, min(1.0, score))
	sarcasm = data.get("sarcasm_flag")
	if sarcasm is None and isinstance(data.get("sarcasm"), bool):
		sarcasm = data.get("sarcasm")
	explanation = data.get("explanation")
	return SentimentResult(label=label, score=score, sarcasm_flag=sarcasm if isinstance(sarcasm, bool) else None, explanation=str(explanation) if explanation else None)


def _fallback_parse(raw: str) -> Dict[str, object]:
	lower = raw.lower()
	label = "neutral"
	if any(word in lower for word in ["positive", "optimistic", "upbeat"]):
		label = "positive"
	elif any(word in lower for word in ["negative", "pessimistic", "critical"]):
		label = "negative"
	elif "mixed" in lower:
		label = "mixed"
	score = 0.5
	if "0." in raw:
		try:
			score = float(re.findall(r"0\.\d+", raw)[0])
		except (ValueError, IndexError):
			pass
	return {"label": label, "score": score}


def _normalize_label(label: str) -> str:
	label = label.lower()
	if label in {"positive", "negative", "neutral", "mixed"}:
		return label
	return "unknown"


async def _generate_implications(
	context_text: str,
	chunks: Sequence[ContextChunk],
	prompt_ref: str,
	language: str,
) -> Tuple[List[ImplicationItem], Dict[str, object]]:
	resp = await call_llm_generate(
		task="qa",
		prompt_ref=prompt_ref,
		variables={"context": context_text},
		language=language or "auto",
		provider_hint=IMPLICATION_MODEL_HINT,
	)
	raw = str(resp.get("output") or "").strip()
	items = _parse_implication_output(raw, chunks)
	if not items and chunks:
		items = [
			ImplicationItem(text="Văn bản hàm ý rằng người dùng kỳ vọng hiệu năng được cải thiện.", spans=[chunks[0].as_span()], confidence=0.5)
		]
	return items[:MAX_IMPLICATIONS], resp


def _parse_implication_output(output: str, chunks: Sequence[ContextChunk]) -> List[ImplicationItem]:
	if not output:
		return []
	chunk_lookup = {chunk.chunk_id.lower(): chunk for chunk in chunks}
	json_items = _parse_implication_json(output, chunk_lookup, chunks)
	if json_items:
		return json_items
	items: List[ImplicationItem] = []
	for line in output.splitlines():
		trimmed = line.strip()
		if not trimmed or trimmed[0] not in "-•0123456789":
			continue
		text_part = trimmed.lstrip("-•0123456789. ").strip()
		if not text_part:
			continue
		span_ids = SEG_PATTERN.findall(text_part)
		clean_text = SEG_MARKER.sub("", text_part).strip()
		spans = [_span_for_id(span_id, chunk_lookup) for span_id in span_ids]
		spans = [span for span in spans if span]
		if not spans and chunks:
			spans = [chunks[0].as_span()]
		confidence = round(min(0.9, 0.6 + 0.05 * len(spans)), 2)
		items.append(ImplicationItem(text=_trim_words(clean_text, 22), spans=spans, confidence=confidence))
	return items


def _parse_implication_json(
	output: str,
	chunk_lookup: Dict[str, ContextChunk],
	chunks: Sequence[ContextChunk],
) -> List[ImplicationItem]:
	try:
		data = json.loads(output)
	except json.JSONDecodeError:
		return []
	raw_items: List[object] = []
	if isinstance(data, dict):
		for key in ("implications", "items", "results"):
			if isinstance(data.get(key), list):
				raw_items = data[key]
				break
	elif isinstance(data, list):
		raw_items = data
	items: List[ImplicationItem] = []
	for item in raw_items:
		if isinstance(item, dict):
			text = str(
				item.get("text")
				or item.get("implication")
				or item.get("summary")
				or ""
			).strip()
			if not text:
				continue
			conf = item.get("confidence")
			conf_val = float(conf) if isinstance(conf, (int, float)) else 0.7
			span_refs: List[SpanRef] = []
			for span_like in item.get("spans") or item.get("span_refs") or []:
				span = _span_from_any(span_like, chunk_lookup)
				if span:
					span_refs.append(span)
			if not span_refs:
				span_ids = item.get("segment_ids") or item.get("segments") or []
				for span_id in span_ids:
					span = _span_for_id(str(span_id), chunk_lookup)
					if span:
						span_refs.append(span)
			if not span_refs and chunks:
				span_refs = [chunks[0].as_span()]
			items.append(
				ImplicationItem(
					text=_trim_words(text, 22),
					spans=span_refs,
					confidence=round(min(0.95, conf_val), 2),
				)
			)
	return items


def _span_for_id(span_id: str, lookup: Dict[str, ContextChunk]) -> SpanRef | None:
	chunk = lookup.get(span_id.lower())
	return chunk.as_span() if chunk else None


def _span_from_any(span_like: object, lookup: Dict[str, ContextChunk]) -> SpanRef | None:
	if isinstance(span_like, dict):
		try:
			return SpanRef.model_validate(span_like)
		except Exception:
			seg_id = span_like.get("segment_id") or span_like.get("chunk_id")
			if seg_id:
				return _span_for_id(str(seg_id), lookup)
	if isinstance(span_like, str):
		return _span_for_id(span_like, lookup)
	return None


def _trim_words(text: str, limit: int) -> str:
	words = text.split()
	if len(words) <= limit:
		return text
	return " ".join(words[:limit])


async def _run_sentiment_async(task: Dict[str, object]) -> Dict[str, object]:
	prompt_ref = (task.get("prompt_ids") or {}).get("sentiment") if isinstance(task.get("prompt_ids"), dict) else None  # type: ignore[arg-type]
	segments = task.get("segments") or []
	payload, llm_resp = await analyze_implication_sentiment(
		context_id=str(task.get("context_id") or ""),
		language=str(task.get("language") or "auto"),
		segments=segments,
		implication_prompt_ref=IMPLICATION_PROMPT_REF,
		sentiment_prompt_ref=prompt_ref or SENTIMENT_PROMPT_REF,
	)
	return {"worker": "sentiment", "ok": True, "output": payload.model_dump(by_alias=True), "llm_call": llm_resp}


@ray.remote
def run_sentiment(task: Dict[str, object]) -> Dict[str, object]:
	return asyncio.run(_run_sentiment_async(task))

