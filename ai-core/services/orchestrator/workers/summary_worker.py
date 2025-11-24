from __future__ import annotations

import asyncio
import math
import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Sequence, Protocol, Union

import ray
from shared.contracts import ContextChunk, SpanRef
from workers.base import call_llm_generate
from workers.utils import (
	ensure_context_id,
	fetch_context_chunks,
	format_context,
	normalize_chunks,
)
from domain.schemas import SummaryWorkerBullet, SummaryWorkerOutput

SUMMARY_PROMPT_REF = os.getenv("SUMMARY_PROMPT_REF", "key:demo.summary.v1")
SUMMARY_MODEL_HINT = os.getenv("SUMMARY_MODEL_HINT", "openai")
SUMMARY_SEGMENT_LIMIT = int(os.getenv("SUMMARY_SEGMENT_LIMIT", "12"))
SUMMARY_MIN_BULLETS = int(os.getenv("SUMMARY_MIN_BULLETS", "3"))
SUMMARY_MAX_BULLETS = int(os.getenv("SUMMARY_MAX_BULLETS", "5"))
SEED_SENTENCE_MAX = 6
SEED_SENTENCE_MIN = 3
SENTENCE_REGEX = re.compile(r"[^.!?]+[.!?]?", re.UNICODE)
TOKEN_REGEX = re.compile(r"[0-9A-Za-zÀ-ỹ]+", re.UNICODE)
SEG_PATTERN = re.compile(r"seg:([0-9a-fA-F\-]{8,})", re.IGNORECASE)
SEG_MARKER = re.compile(r"\[seg:[0-9a-fA-F\-]{8,}\]", re.IGNORECASE)
STOPWORDS = {
	"the", "a", "an", "and", "or", "but", "to", "of", "in", "on", "for", "is", "are", "was", "were", "be",
	"with", "by", "as", "at", "that", "this", "it", "its", "from", "và", "là", "của", "cho", "trên",
	"một", "các", "những", "được", "với", "từ", "đã", "trong", "khi", "đang",
}


@dataclass
class SeedSentence:
	chunk_id: str
	text: str
	start_offset: int | None
	end_offset: int | None
	sentence_index: int
	tokens: List[str] = field(default_factory=list)
	score: float = 0.0


class SummaryVerifier(Protocol):
	async def verify(
		self,
		context_id: str,
		bullets: Sequence[SummaryWorkerBullet],
		segments: Sequence[ContextChunk],
	) -> Sequence[SummaryWorkerBullet]:
		...


class SummaryPipeline:
	def __init__(
		self,
		segment_limit: int,
		min_bullets: int,
		max_bullets: int,
		model_hint: str,
		verifier: SummaryVerifier | None = None,
	):
		self.segment_limit = segment_limit
		self.min_bullets = max(1, min_bullets)
		self.max_bullets = max(self.min_bullets, max_bullets)
		self.model_hint = model_hint
		self.verifier = verifier

	async def run(
		self,
		context_id: str,
		segments: Sequence[ContextChunk],
		language: str,
		prompt_ref: str,
	) -> tuple[SummaryWorkerOutput, Dict[str, object]]:
		chunks = list(segments[: self.segment_limit])
		if not chunks:
			raise ValueError("segments_required")
		context_text = format_context(chunks)
		seeds = _build_seed_sentences(chunks)
		llm_resp = await call_llm_generate(
			task="summary",
			prompt_ref=prompt_ref,
			variables={
				"context": context_text,
				"seeds": _format_seed_block(seeds),
			},
			language=language or "auto",
			provider_hint=self.model_hint,
		)
		raw_output = str(llm_resp.get("output") or "").strip()
		bullets = _parse_llm_output(raw_output, chunks, self.max_bullets)
		if self.verifier:
			try:
				bullets = list(
					await self.verifier.verify(
						context_id=context_id,
						bullets=bullets,
						segments=chunks,
					)
				)
			except Exception:
				pass
		if len(bullets) < self.min_bullets:
			bullets.extend(_fallback_from_seeds(seeds, chunks, self.min_bullets - len(bullets)))
		payload = SummaryWorkerOutput(
			context_id=context_id,
			bullets=bullets[: self.max_bullets],
			seed_sentences=[seed.text for seed in seeds],
		)
		return payload, llm_resp


PIPELINE = SummaryPipeline(
	segment_limit=SUMMARY_SEGMENT_LIMIT,
	min_bullets=SUMMARY_MIN_BULLETS,
	max_bullets=SUMMARY_MAX_BULLETS,
	model_hint=SUMMARY_MODEL_HINT,
	verifier=None,
)


async def summarize_context(
	context_id: str,
	*,
	language: str = "auto",
	prompt_ref: str | None = None,
	segments: Sequence[Union[ContextChunk, Dict[str, object]]] | None = None,
) -> tuple[SummaryWorkerOutput, Dict[str, object]]:
	normalized_segments = normalize_chunks(segments or [])
	effective_context_id = ensure_context_id(context_id, normalized_segments)
	final_segments = normalized_segments
	if not final_segments:
		final_segments = await fetch_context_chunks(effective_context_id, SUMMARY_SEGMENT_LIMIT)
	payload, llm_resp = await PIPELINE.run(
		context_id=effective_context_id,
		segments=final_segments,
		language=language or "auto",
		prompt_ref=prompt_ref or SUMMARY_PROMPT_REF,
	)
	return payload, llm_resp


async def _run_summary_async(task: Dict[str, object]) -> Dict[str, object]:
	prompt_ref = ((task.get("prompt_ids") or {}) if isinstance(task.get("prompt_ids"), dict) else {}).get("summary")  # type: ignore[arg-type]
	language = str(task.get("language") or "auto")
	context_id = str(task.get("context_id") or "")
	raw_segments = task.get("segments") or []
	payload, llm_resp = await summarize_context(
		context_id=context_id,
		language=language,
		prompt_ref=prompt_ref,
		segments=raw_segments,
	)
	return {"worker": "summary", "ok": True, "output": payload.model_dump(by_alias=True), "llm_call": llm_resp}


@ray.remote
def run_summary(task: Dict[str, object]) -> Dict[str, object]:
	return asyncio.run(_run_summary_async(task))


def _build_seed_sentences(chunks: Sequence[ContextChunk]) -> List[SeedSentence]:
	sentences: List[SeedSentence] = []
	global_index = 0
	for chunk in chunks:
		text = chunk.text.strip()
		if not text:
			continue
		base_offset = chunk.start_offset or 0
		for local_idx, match in enumerate(SENTENCE_REGEX.finditer(text)):
			sentence = match.group().strip()
			if len(sentence) < 20:
				continue
			rel_start = match.start()
			rel_end = match.end()
			index = chunk.sentence_index if chunk.sentence_index is not None else global_index
			sentences.append(
				SeedSentence(
					chunk_id=chunk.chunk_id,
					text=sentence,
					start_offset=base_offset + rel_start if chunk.start_offset is not None else None,
					end_offset=base_offset + rel_end if chunk.start_offset is not None else None,
					sentence_index=index + local_idx,
				)
			)
		global_index += 1
	_score_sentences(sentences)
	target = min(SEED_SENTENCE_MAX, max(SEED_SENTENCE_MIN, len(sentences)))
	selected = sorted(sentences, key=lambda s: (-s.score, s.sentence_index))[:target]
	return sorted(selected, key=lambda s: s.sentence_index)


def _score_sentences(sentences: Sequence[SeedSentence]) -> None:
	total = len(sentences)
	if total == 0:
		return
	doc_freq: Dict[str, int] = {}
	for sentence in sentences:
		sentence.tokens = _tokenize(sentence.text)
		for token in set(sentence.tokens):
			doc_freq[token] = doc_freq.get(token, 0) + 1
	for idx, sentence in enumerate(sentences):
		if not sentence.tokens:
			sentence.score = 0.0
			continue
		token_counts: Dict[str, int] = {}
		for token in sentence.tokens:
			token_counts[token] = token_counts.get(token, 0) + 1
		score = 0.0
		for token, count in token_counts.items():
			idf = math.log((1 + total) / (1 + doc_freq.get(token, 0))) + 1.0
			tf = count / len(sentence.tokens)
			score += tf * idf
		position_bonus = 1.0 - (idx / max(total, 1))
		sentence.score = score * (1.0 + 0.15 * position_bonus)


def _tokenize(text: str) -> List[str]:
	return [token for token in (w.lower() for w in TOKEN_REGEX.findall(text.lower())) if token not in STOPWORDS]


def _format_seed_block(seeds: Sequence[SeedSentence]) -> str:
	return "\n".join(f"- [seg:{seed.chunk_id}] {seed.text.strip()}" for seed in seeds)


def _parse_llm_output(raw_output: str, chunks: Sequence[ContextChunk], max_bullets: int) -> List[SummaryWorkerBullet]:
	if not raw_output:
		return []
	chunk_lookup = {chunk.chunk_id.lower(): chunk for chunk in chunks}
	bullets: List[SummaryWorkerBullet] = []
	for line in raw_output.splitlines():
		trimmed = line.strip()
		if not trimmed:
			continue
		if trimmed[0] not in "-•0123456789":
			continue
		text_part = trimmed.lstrip("-•0123456789. ").strip()
		if not text_part:
			continue
		span_ids = SEG_PATTERN.findall(text_part)
		clean_text = _trim_words(SEG_MARKER.sub("", text_part).strip(), 18)
		spans = _spans_from_ids(span_ids, chunk_lookup)
		if not spans and chunks:
			spans = [chunks[0].as_span()]
		confidence = _estimate_confidence(spans, len(span_ids))
		bullets.append(SummaryWorkerBullet(bullet=clean_text, spans=spans, confidence=confidence))
		if len(bullets) >= max_bullets:
			break
	return bullets


def _spans_from_ids(segment_ids: Sequence[str], lookup: Dict[str, ContextChunk]) -> List[SpanRef]:
	spans: List[SpanRef] = []
	for seg_id in segment_ids:
		segment = lookup.get(seg_id.lower())
		if segment:
			spans.append(segment.as_span())
	return spans


def _estimate_confidence(spans: Sequence[SpanRef], cited_markers: int) -> float:
	base = 0.65
	source_bonus = min(len(spans), 3) * 0.08
	citation_bonus = 0.05 if cited_markers else 0.0
	return round(min(0.95, base + source_bonus + citation_bonus), 2)


def _fallback_from_seeds(seeds: Sequence[SeedSentence], chunks: Sequence[ContextChunk], needed: int) -> List[SummaryWorkerBullet]:
	if needed <= 0:
		return []
	chunk_lookup = {chunk.chunk_id: chunk for chunk in chunks}
	results: List[SummaryWorkerBullet] = []
	for seed in seeds:
		if len(results) >= needed:
			break
		chunk = chunk_lookup.get(seed.chunk_id)
		if not chunk:
			continue
		text = _trim_words(seed.text, 18)
		spans = [chunk.as_span()]
		results.append(SummaryWorkerBullet(bullet=text, spans=spans, confidence=0.6))
	return results


def _trim_words(text: str, max_words: int) -> str:
	words = text.split()
	if len(words) <= max_words:
		return text
	return " ".join(words[:max_words])
