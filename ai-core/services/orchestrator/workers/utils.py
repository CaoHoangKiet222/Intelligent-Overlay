from __future__ import annotations

from typing import Dict, List, Mapping, Sequence, Tuple, Union

import httpx
from shared.contracts import ContextChunk, SpanRef
from shared.config.base import get_base_config

_retrieval_base = get_base_config()
RETRIEVAL_SERVICE_BASE_URL = _retrieval_base.retrieval_service_base_url


def normalize_chunks(segments: Sequence[Union[ContextChunk, Mapping[str, object]]]) -> List[ContextChunk]:
	normalized: List[ContextChunk] = []
	for seg in segments:
		if isinstance(seg, ContextChunk):
			normalized.append(seg)
		elif isinstance(seg, Mapping):
			normalized.append(ContextChunk.model_validate(seg))
	return normalized


def ensure_context_id(context_id: str, segments: Sequence[ContextChunk]) -> str:
	if context_id:
		return context_id
	if segments:
		first = segments[0]
		return first.document_id or first.chunk_id
	raise ValueError("context_id_missing")


def format_context(chunks: Sequence[ContextChunk]) -> str:
	return "\n".join(f"[seg:{chunk.chunk_id}] {chunk.text.strip()}" for chunk in chunks if chunk.text.strip())


async def fetch_context_chunks(context_id: str, limit: int) -> List[ContextChunk]:
	url = f"{RETRIEVAL_SERVICE_BASE_URL.rstrip('/')}/retrieval/context/{context_id}"
	async with httpx.AsyncClient(timeout=10.0) as client:
		resp = await client.get(url, params={"limit": limit})
		resp.raise_for_status()
		body = resp.json()
	segments = body.get("segments") or []
	return normalize_chunks(segments)


async def search_spans(
	context_id: str,
	query: str,
	top_k: int,
	mode: str = "hybrid",
) -> List[Tuple[SpanRef, str]]:
	payload: Dict[str, object] = {
		"context_id": context_id,
		"query": query,
		"top_k": top_k,
		"mode": mode,
	}
	url = f"{RETRIEVAL_SERVICE_BASE_URL.rstrip('/')}/retrieval/search"
	async with httpx.AsyncClient(timeout=12.0) as client:
		resp = await client.post(url, json=payload)
		resp.raise_for_status()
		body = resp.json()
	results = []
	for item in body.get("results") or []:
		raw_span = item.get("span")
		if not raw_span:
			continue
		span = SpanRef.model_validate(raw_span)
		results.append((span, item.get("snippet") or ""))
	return results

