import os
from typing import Dict, Any, Optional

import httpx

BASE = os.getenv("MODEL_ADAPTER_BASE_URL", "http://model-adapter:8000").rstrip("/")


async def llm_generate(prompt_ref: str, variables: Dict[str, Any], language: str, task: str, model_hint: Optional[str] = None) -> Dict[str, Any]:
	payload: Dict[str, Any] = {
		"prompt_ref": prompt_ref,
		"variables": variables,
		"language": language,
		"task": task,
	}
	if model_hint:
		payload["provider_hint"] = model_hint
	async with httpx.AsyncClient(timeout=30.0) as client:
		r = await client.post(f"{BASE}/model/generate", json=payload)
		r.raise_for_status()
		return r.json()


