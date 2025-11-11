import os
import httpx
from typing import List, Dict, Any
from config import MODEL_ADAPTER_BASE_URL, EMBED_MODEL_HINT


async def embed_texts(texts: List[str]) -> Dict[str, Any]:
	async with httpx.AsyncClient(timeout=30.0) as client:
		r = await client.post(f"{MODEL_ADAPTER_BASE_URL}/embed", json={"texts": texts, "model_hint": EMBED_MODEL_HINT})
		r.raise_for_status()
		return r.json()


