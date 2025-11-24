from __future__ import annotations

import asyncio
import json
import os
import re
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple, Union

import ray
from shared.contracts import ContextChunk, SpanRef
from domain.schemas import LogicBiasFinding, LogicBiasOutput
from workers.base import call_llm_generate
from workers.utils import ensure_context_id, fetch_context_chunks, normalize_chunks

LOGIC_BIAS_PROMPT_REF = os.getenv("LOGIC_BIAS_PROMPT_REF", "key:demo.logic_bias.v1")
LOGIC_BIAS_MODEL_HINT = os.getenv("LOGIC_BIAS_MODEL_HINT", "openai")
LOGIC_BIAS_SEGMENT_LIMIT = int(os.getenv("LOGIC_BIAS_SEGMENT_LIMIT", "12"))
LOGIC_BIAS_MAX_FINDINGS = int(os.getenv("LOGIC_BIAS_MAX_FINDINGS", "6"))
HEURISTIC_KEYWORDS = [
	r"\ball\b",
	r"\bnever\b",
	r"\balways\b",
	r"\bobviously\b",
	r"\bclearly\b",
	r"\beveryone knows\b",
	r"\bno evidence\b",
	r"\bmust\b",
]
HEURISTIC_PATTERNS = [re.compile(pattern, re.IGNORECASE) for pattern in HEURISTIC_KEYWORDS]


@dataclass
class HeuristicHit:
	chunk: ContextChunk
	start: int
	end: int
	snippet: str


async def analyze_logic_bias(
	context_id: str,
	*,
	language: str = "auto",
	segments: Sequence[Union[ContextChunk, Dict[str, object]]] | None = None,
	prompt_ref: str | None = None,
) -> Tuple[LogicBiasOutput, Dict[str, object]]:
	normalized_segments = normalize_chunks(segments or [])
	effective_context_id = ensure_context_id(context_id, normalized_segments)
	final_segments = normalized_segments or await fetch_context_chunks(effective_context_id, LOGIC_BIAS_SEGMENT_LIMIT)

	hits = _scan_for_hits(final_segments)
	findings, llm_resp = await _validate_hits(
		context_id=effective_context_id,
		hits=hits[:LOGIC_BIAS_MAX_FINDINGS],
		prompt_ref=prompt_ref or LOGIC_BIAS_PROMPT_REF,
		language=language,
	)
	if not findings and final_segments:
		fallback_span = final_segments[0].as_span()
		findings = [
			LogicBiasFinding(
				type="generalization",
				span=fallback_span,
				explanation="Không phát hiện rõ ràng nhưng cần xem lại lập luận mở đầu.",
				severity=1,
			)
		]
	payload = LogicBiasOutput(context_id=effective_context_id, findings=findings)
	return payload, llm_resp


def _scan_for_hits(chunks: Sequence[ContextChunk]) -> List[HeuristicHit]:
	results: List[HeuristicHit] = []
	for chunk in chunks:
		text = chunk.text
		if not text:
			continue
		matches: List[Tuple[int, int]] = []
		for pattern in HEURISTIC_PATTERNS:
			for match in pattern.finditer(text):
				matches.append((match.start(), match.end()))
		for start, end in matches:
			snippet = text[max(0, start - 60): min(len(text), end + 160)].strip()
			results.append(HeuristicHit(chunk=chunk, start=start, end=end, snippet=snippet))
	return results


async def _validate_hits(
	context_id: str,
	hits: Sequence[HeuristicHit],
	prompt_ref: str,
	language: str,
) -> Tuple[List[LogicBiasFinding], Dict[str, object]]:
	if not hits:
		return [], {}
	findings: List[LogicBiasFinding] = []
	llm_resps: List[Dict[str, object]] = []

	async def _call(hit: HeuristicHit) -> Tuple[LogicBiasFinding | None, Dict[str, object]]:
		span_text = hit.snippet or hit.chunk.text[:200]
		resp = await call_llm_generate(
			task="logic_bias",
			prompt_ref=prompt_ref,
			variables={"snippet": span_text, "context_id": context_id},
			language=language or "auto",
			provider_hint=LOGIC_BIAS_MODEL_HINT,
		)
		text = str(resp.get("output") or "").strip()
		finding = _parse_bias_output(hit, text)
		return finding, resp

	tasks = [_call(hit) for hit in hits]
	results = await asyncio.gather(*tasks, return_exceptions=True)
	for result in results:
		if isinstance(result, Exception):
			continue
		finding, resp = result
		if finding:
			findings.append(finding)
			llm_resps.append(resp)
	last_resp = llm_resps[-1] if llm_resps else {}
	return findings, last_resp


def _parse_bias_output(hit: HeuristicHit, output: str) -> LogicBiasFinding | None:
	if not output:
		return None
	json_result = _parse_bias_json(hit, output)
	if json_result is not None:
		return json_result
	lower = output.lower()
	if "no issue" in lower or "not biased" in lower:
		return None
	type_match = re.search(r"type[:\-]?\s*([a-zA-Z\s]+)", output)
	type_name = type_match.group(1).strip() if type_match else "potential_bias"
	severity_match = re.search(r"severity[:\-]?\s*(\d)", output)
	severity = 2
	if severity_match:
		try:
			severity = max(1, min(3, int(severity_match.group(1))))
		except ValueError:
			pass
	explanation_match = re.search(r"explanation[:\-]?\s*(.+)", output, re.IGNORECASE)
	explanation = explanation_match.group(1).strip() if explanation_match else output[:300]
	span = _span_from_hit(hit)
	return LogicBiasFinding(type=type_name, span=span, explanation=explanation, severity=severity)


def _parse_bias_json(hit: HeuristicHit, output: str) -> LogicBiasFinding | None:
	try:
		data = json.loads(output)
	except json.JSONDecodeError:
		return None
	if not isinstance(data, dict):
		return None
	if data.get("valid") is False or data.get("has_issue") is False:
		return None
	type_name = str(data.get("type") or data.get("label") or "potential_bias").strip()
	explanation = str(data.get("explanation") or data.get("summary") or "").strip() or hit.snippet[:300]
	severity_val = data.get("severity") or data.get("severity_level")
	try:
		severity = int(severity_val)
	except (TypeError, ValueError):
		severity = 2
	severity = max(1, min(3, severity))
	span_data = data.get("span") or data.get("citation")
	if isinstance(span_data, dict):
		try:
			span = SpanRef.model_validate(span_data)
		except Exception:
			span = _span_from_hit(hit)
	elif isinstance(span_data, str):
		span = SpanRef(chunk_id=span_data, text_preview=hit.snippet[:200])
	else:
		span = _span_from_hit(hit)
	return LogicBiasFinding(type=type_name, span=span, explanation=explanation, severity=severity)


def _span_from_hit(hit: HeuristicHit) -> SpanRef:
	if hit.chunk.start_offset is not None:
		start = hit.chunk.start_offset + hit.start
		end = hit.chunk.start_offset + hit.end
	else:
		start = hit.start
		end = hit.end
	return SpanRef(
		chunk_id=hit.chunk.chunk_id,
		start_offset=start,
		end_offset=end,
		text_preview=hit.snippet[:200],
		sentence_index=hit.chunk.sentence_index,
	)


async def _run_logic_bias_async(task: Dict[str, object]) -> Dict[str, object]:
	prompt_ref = (task.get("prompt_ids") or {}).get("logic_bias") if isinstance(task.get("prompt_ids"), dict) else None  # type: ignore[arg-type]
	segments = task.get("segments") or []
	payload, llm_resp = await analyze_logic_bias(
		context_id=str(task.get("context_id") or ""),
		language=str(task.get("language") or "auto"),
		segments=segments,
		prompt_ref=prompt_ref or LOGIC_BIAS_PROMPT_REF,
	)
	return {"worker": "logic_bias", "ok": True, "output": payload.model_dump(by_alias=True), "llm_call": llm_resp}


@ray.remote
def run_logic_bias(task: Dict[str, object]) -> Dict[str, object]:
	return asyncio.run(_run_logic_bias_async(task))
