from typing import Any, Dict, Optional
import httpx


class RetrievalClient:
	def __init__(self, base_url: str, timeout: float = 30.0):
		self._base_url = base_url.rstrip("/")
		self._timeout = timeout

	async def ingest_text(self, text: str, url: Optional[str], locale: Optional[str]) -> Dict[str, Any]:
		payload = {"raw_text": text, "url": url, "locale": locale or "auto"}
		async with httpx.AsyncClient(timeout=self._timeout) as client:
			resp = await client.post(f"{self._base_url}/ingestion/normalize_and_index", json=payload)
			resp.raise_for_status()
			return resp.json()

	async def search(self, context_id: str, query: str, top_k: int = 5, mode: str = "hybrid") -> Dict[str, Any]:
		payload = {"context_id": context_id, "query": query, "top_k": top_k, "mode": mode}
		async with httpx.AsyncClient(timeout=self._timeout) as client:
			resp = await client.post(f"{self._base_url}/retrieval/search", json=payload)
			resp.raise_for_status()
			return resp.json()

