from __future__ import annotations

import re
from typing import Dict, List, Tuple

from domain.schemas import ContextChunk, SpanRef


SEG_PATTERN = re.compile(r"seg:([0-9a-fA-F\-]{8,})", re.IGNORECASE)


def build_context(segments: List[ContextChunk]) -> Tuple[str, Dict[str, ContextChunk]]:
	lookup = {seg.chunk_id.lower(): seg for seg in segments}
	text = "\n".join(f"[seg:{seg.chunk_id.lower()}] {seg.text}" for seg in segments)
	return text, lookup


def extract_segment_ids(text: str) -> List[str]:
	return [match.lower() for match in SEG_PATTERN.findall(text)]


def make_span_refs(segment_ids: List[str], lookup: Dict[str, ContextChunk], fallback_index: int) -> List[SpanRef]:
	if not segment_ids:
		return [fallback_span(list(lookup.values()), fallback_index)]
	refs: List[SpanRef] = []
	for seg_id in segment_ids:
		seg = lookup.get(seg_id)
		if seg:
			refs.append(to_span(seg))
	if refs:
		return refs
	return [fallback_span(list(lookup.values()), fallback_index)]


def fallback_span(segments: List[ContextChunk], fallback_index: int) -> SpanRef:
	if not segments:
		return SpanRef(chunk_id="unknown", text_preview=None)
	seg = segments[min(fallback_index, len(segments) - 1)]
	return to_span(seg)


def to_span(seg: ContextChunk) -> SpanRef:
	return SpanRef(
		chunk_id=seg.chunk_id,
		start_offset=seg.start_offset,
		end_offset=seg.end_offset,
		text_preview=seg.text[:160],
	)


def parse_labeled_block(block: str) -> Tuple[str, str, str]:
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


def parse_implication_block(text: str) -> Tuple[List[str], str]:
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


def parse_sentiment(line: str) -> Tuple[str, str]:
	if ":" not in line:
		return "neutral", line or ""
	_, rest = line.split(":", 1)
	parts = rest.split("-", 1)
	label = parts[0].strip().lower()
	if label not in {"positive", "negative", "neutral", "mixed"}:
		label = "neutral"
	explanation = parts[1].strip() if len(parts) > 1 else rest.strip()
	return label, explanation or "Không có giải thích chi tiết."


def parse_logic_bias_line(line: str) -> Dict[str, str] | None:
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


