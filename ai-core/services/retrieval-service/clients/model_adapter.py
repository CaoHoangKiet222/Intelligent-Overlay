import os
import httpx
from typing import List, Dict, Any
from app.config import MODEL_ADAPTER_BASE_URL, EMBED_MODEL_HINT
from shared.config.base import get_base_config


async def embed_texts(texts: List[str]) -> Dict[str, Any]:
	timeout_config = get_base_config().timeout_config
	timeout = timeout_config.services.model_adapter
	async with httpx.AsyncClient(timeout=timeout) as client:
		r = await client.post(f"{MODEL_ADAPTER_BASE_URL}/model/embed", json={"texts": texts, "model_hint": EMBED_MODEL_HINT})
		r.raise_for_status()
		return r.json()


