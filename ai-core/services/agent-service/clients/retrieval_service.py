import os
from typing import Dict, Any

import httpx

BASE = os.getenv("RETRIEVAL_BASE_URL", "http://retrieval-service:8000").rstrip("/")


async def hybrid_search(query: str, top_k: int = 6) -> Dict[str, Any]:
	async with httpx.AsyncClient(timeout=20.0) as client:
		r = await client.post(f"{BASE}/search", json={"query": query, "top_k": top_k, "vec_k": 100, "trgm_k": 200})
		r.raise_for_status()
		return r.json()


async def search_context_spans(context_id: str, query: str, top_k: int = 5, mode: str = "hybrid") -> Dict[str, Any]:
	payload = {
		"context_id": context_id,
		"query": query,
		"top_k": top_k,
		"mode": mode,
	}
	async with httpx.AsyncClient(timeout=15.0) as client:
		resp = await client.post(f"{BASE}/retrieval/search", json=payload)
		resp.raise_for_status()
		return resp.json()


