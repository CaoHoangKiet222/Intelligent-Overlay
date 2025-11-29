from __future__ import annotations

import asyncio
import json
import os
import re
from typing import Dict, List, Sequence, Tuple, Union

import ray
from shared.contracts import ContextChunk, SpanRef
from domain.schemas import ArgumentClaim, ArgumentWorkerOutput
from workers.base import call_llm_generate
from workers.utils import (
	ensure_context_id,
	fetch_context_chunks,
	format_context,
	normalize_chunks,
	search_spans,
)
from app.config import OrchestratorConfig

_config = OrchestratorConfig.from_env()

CLAIM_PROMPT_REF = os.getenv("ARGUMENT_CLAIM_PROMPT_REF", "key:demo.argument.claims.v1")
REASON_PROMPT_REF = os.getenv("ARGUMENT_REASON_PROMPT_REF", "key:demo.argument.reasoning.v1")
ARGUMENT_SEGMENT_LIMIT = int(os.getenv("ARGUMENT_SEGMENT_LIMIT", "12"))
ARGUMENT_MIN_CLAIMS = int(os.getenv("ARGUMENT_MIN_CLAIMS", "3"))
ARGUMENT_MAX_CLAIMS = int(os.getenv("ARGUMENT_MAX_CLAIMS", "7"))
ARGUMENT_EVIDENCE_TOP_K = int(os.getenv("ARGUMENT_EVIDENCE_TOP_K", "3"))
CLAIM_PATTERN = re.compile(r"^[\-\d\.\)]\s*(.+)", re.MULTILINE)


async def analyze_arguments(
	context_id: str,
	*,
	language: str = "auto",
	segments: Sequence[Union[ContextChunk, Dict[str, object]]] | None = None,
	claim_prompt_ref: str | None = None,
	reason_prompt_ref: str | None = None,
) -> Tuple[ArgumentWorkerOutput, Dict[str, object]]:
	normalized_segments = normalize_chunks(segments or [])
	effective_context_id = ensure_context_id(context_id, normalized_segments)
	final_segments = normalized_segments or await fetch_context_chunks(effective_context_id, ARGUMENT_SEGMENT_LIMIT)
	context_text = format_context(final_segments)

	claims, claim_llm_resp = await _mine_claims(
		context_text=context_text,
		prompt_ref=claim_prompt_ref or CLAIM_PROMPT_REF,
		language=language,
	)
	if not claims and final_segments:
		claims = [chunk.text.strip()[:200] for chunk in final_segments[:ARGUMENT_MIN_CLAIMS] if chunk.text.strip()]

	evidence = await _gather_evidence(effective_context_id, claims)
	reasonings, reasoning_conf, last_reason_resp = await _write_reasonings(
		claims=claims,
		evidence=evidence,
		context_text=context_text,
		prompt_ref=reason_prompt_ref or REASON_PROMPT_REF,
		language=language,
	)
	findings: List[ArgumentClaim] = []
	for claim in claims[:ARGUMENT_MAX_CLAIMS]:
		spans = evidence.get(claim, {}).get("spans") or []
		if not spans and final_segments:
			spans = [final_segments[0].as_span()]
		reasoning_text = reasonings.get(claim) or ""
		confidence = _confidence_from_evidence(spans, reasoning_text, reasoning_conf.get(claim))
		findings.append(
			ArgumentClaim(
				claim=_trim_claim(claim),
				evidence_spans=spans[:ARGUMENT_EVIDENCE_TOP_K],
				reasoning=reasoning_text,
				confidence=confidence,
			)
		)
	payload = ArgumentWorkerOutput(context_id=effective_context_id, claims=findings)
	return payload, last_reason_resp or claim_llm_resp


async def _mine_claims(context_text: str, prompt_ref: str, language: str) -> Tuple[List[str], Dict[str, object]]:
	llm_resp = await call_llm_generate(
		task="argument",
		prompt_ref=prompt_ref,
		variables={"context": context_text},
		language=language or "auto",
		provider_hint=_config.argument_claim_model_hint,
	)
	raw = str(llm_resp.get("output") or "").strip()
	claims = _parse_claims(raw)
	return claims[:ARGUMENT_MAX_CLAIMS], llm_resp


def _parse_claims(output: str) -> List[str]:
	json_claims = _parse_claims_json(output)
	if json_claims:
		return json_claims
	
	lines = []
	for line in output.splitlines():
		line = line.strip()
		if not line:
			continue
		
		if line.upper().startswith("ANSWER:") or line.upper().startswith("CITATIONS:") or line.upper().startswith("CONFIDENCE:"):
			continue
		
		match = CLAIM_PATTERN.match(line)
		if match:
			claim_text = match.group(1).strip()
			if len(claim_text.split()) >= 4:
				lines.append(claim_text)
	
	if not lines and output:
		cleaned = output.strip()
		if not cleaned.upper().startswith("ANSWER:"):
			lines = [cleaned]
	
	return [claim for claim in lines if len(claim.split()) >= 4] if lines else []


def _parse_claims_json(output: str) -> List[str]:
	try:
		data = json.loads(output)
	except json.JSONDecodeError:
		return []
	items: List[object] = []
	if isinstance(data, dict):
		for key in ("claims", "items", "results"):
			if isinstance(data.get(key), list):
				items = data[key]
				break
	elif isinstance(data, list):
		items = data
	results: List[str] = []
	for item in items:
		text = ""
		if isinstance(item, dict):
			text = str(item.get("claim") or item.get("text") or item.get("statement") or "").strip()
		elif isinstance(item, str):
			text = item.strip()
		if text:
			results.append(text)
	return results


async def _gather_evidence(context_id: str, claims: Sequence[str]) -> Dict[str, Dict[str, List[SpanRef] | List[str]]]:
	evidence: Dict[str, Dict[str, List[SpanRef] | List[str]]] = {}
	tasks = [
		search_spans(context_id=context_id, query=claim, top_k=ARGUMENT_EVIDENCE_TOP_K)
		for claim in claims
	]
	results = await asyncio.gather(*tasks, return_exceptions=True)
	for claim, result in zip(claims, results):
		spans: List[SpanRef] = []
		snippets: List[str] = []
		if isinstance(result, Exception):
			evidence[claim] = {"spans": spans, "snippets": snippets}
			continue
		for span, snippet in result:
			spans.append(span)
			snippets.append(snippet)
		evidence[claim] = {"spans": spans, "snippets": snippets}
	return evidence


async def _write_reasonings(
	claims: Sequence[str],
	evidence: Dict[str, Dict[str, List[SpanRef] | List[str]]],
	context_text: str,
	prompt_ref: str,
	language: str,
) -> Tuple[Dict[str, str], Dict[str, float], Dict[str, object]]:
	if not claims:
		return {}, {}, {}
	reason_map: Dict[str, str] = {}
	reason_conf: Dict[str, float] = {}
	llm_responses: List[Dict[str, object]] = []

	async def _reason_for_claim(claim: str) -> Tuple[Dict[str, object], Dict[str, object]]:
		snippets = evidence.get(claim, {}).get("snippets") or []
		snippet_block = "\n".join(f"- {snippet}" for snippet in snippets if snippet) or "No direct snippet available."
		resp = await call_llm_generate(
			task="argument",
			prompt_ref=prompt_ref,
			variables={"context": context_text, "claim": claim, "evidence": snippet_block},
			language=language or "auto",
			provider_hint=_config.argument_reason_model_hint,
		)
		text = str(resp.get("output") or "").strip()
		return _parse_reasoning_output(text), resp

	reason_tasks = [_reason_for_claim(claim) for claim in claims[:ARGUMENT_MAX_CLAIMS]]
	results = await asyncio.gather(*reason_tasks, return_exceptions=True)
	for claim, result in zip(claims, results):
		if isinstance(result, Exception):
			continue
		parsed, resp = result
		reason_text = str(parsed.get("reasoning") or parsed.get("explanation") or "").strip()
		if reason_text:
			reason_map[claim] = reason_text
		conf = parsed.get("confidence")
		if isinstance(conf, (int, float)):
			reason_conf[claim] = float(conf)
		llm_responses.append(resp)
	last_resp = llm_responses[-1] if llm_responses else {}
	return reason_map, reason_conf, last_resp


def _parse_reasoning_output(raw: str) -> Dict[str, object]:
	try:
		data = json.loads(raw)
		if isinstance(data, dict):
			return data
	except json.JSONDecodeError:
		pass
	
	cleaned = raw.strip()
	if cleaned.upper().startswith("ANSWER:") or cleaned.upper().startswith("CITATIONS:") or cleaned.upper().startswith("CONFIDENCE:"):
		lines = cleaned.splitlines()
		reasoning_parts = []
		for line in lines:
			line = line.strip()
			if line.upper().startswith("REASONING:"):
				reasoning_parts.append(line.split(":", 1)[1].strip())
			elif not line.upper().startswith(("ANSWER:", "CITATIONS:", "CONFIDENCE:")):
				reasoning_parts.append(line)
		if reasoning_parts:
			return {"reasoning": " ".join(reasoning_parts)}
	
	return {"reasoning": cleaned}


def _confidence_from_evidence(spans: Sequence[SpanRef], reasoning: str, reasoning_conf: float | None) -> float:
	base = 0.55 + 0.08 * min(len(spans), 3)
	if len(reasoning.split()) > 12:
		base += 0.05
	if reasoning_conf is not None:
		base = max(base, min(0.95, reasoning_conf))
	return round(min(0.95, base), 2)


def _trim_claim(claim: str) -> str:
	return claim[:280].rstrip()


async def _run_argument_async(task: Dict[str, object]) -> Dict[str, object]:
	prompt_ref = (task.get("prompt_ids") or {}).get("argument") if isinstance(task.get("prompt_ids"), dict) else None  # type: ignore[arg-type]
	segments = task.get("segments") or []
	payload, llm_resp = await analyze_arguments(
		context_id=str(task.get("context_id") or ""),
		language=str(task.get("language") or "auto"),
		segments=segments,
		claim_prompt_ref=prompt_ref or CLAIM_PROMPT_REF,
		reason_prompt_ref=REASON_PROMPT_REF,
	)
	return {"worker": "argument", "ok": True, "output": payload.model_dump(by_alias=True), "llm_call": llm_resp}


@ray.remote
def run_argument(task: Dict[str, object]) -> Dict[str, object]:
	return asyncio.run(_run_argument_async(task))
