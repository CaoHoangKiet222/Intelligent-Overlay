import os, httpx
from typing import Dict, Any

BASE = os.getenv("RETRIEVAL_BASE_URL", "http://retrieval-service:8000")


async def hybrid_search(query: str, top_k: int = 6) -> Dict[str, Any]:
	async with httpx.AsyncClient(timeout=20.0) as client:
		r = await client.post(f"{BASE}/search", json={"query": query, "top_k": top_k, "vec_k": 100, "trgm_k": 200})
		r.raise_for_status()
		return r.json()


