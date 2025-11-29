import os
from typing import Dict, Any

import httpx
from shared.config.base import get_base_config

BASE = os.getenv("RETRIEVAL_BASE_URL", "http://retrieval-service:8000").rstrip("/")


async def hybrid_search(query: str, top_k: int = 6) -> Dict[str, Any]:
	timeout_config = get_base_config().timeout_config
	timeout = timeout_config.services.retrieval_service
	async with httpx.AsyncClient(timeout=timeout) as client:
		r = await client.post(f"{BASE}/search", json={"query": query, "top_k": top_k, "vec_k": 100, "trgm_k": 200})
		r.raise_for_status()
		return r.json()


async def search_context_spans(context_id: str, query: str, top_k: int = 5, mode: str = "hybrid") -> Dict[str, Any]:
	timeout_config = get_base_config().timeout_config
	timeout = timeout_config.workers.retrieval_search
	payload = {
		"context_id": context_id,
		"query": query,
		"top_k": top_k,
		"mode": mode,
	}
	async with httpx.AsyncClient(timeout=timeout) as client:
		resp = await client.post(f"{BASE}/retrieval/search", json=payload)
		resp.raise_for_status()
		return resp.json()


