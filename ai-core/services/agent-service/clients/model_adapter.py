import os, httpx
from typing import Dict, Any, Optional

BASE = os.getenv("MODEL_ADAPTER_BASE_URL", "http://model-adapter:8000")


async def llm_generate(prompt: str, context: str, language: str, model_hint: Optional[str] = None) -> Dict[str, Any]:
	async with httpx.AsyncClient(timeout=30.0) as client:
		r = await client.post(
			f"{BASE}/generate",
			json={"prompt": prompt, "context": context, "language": language, "provider_hint": model_hint},
		)
		r.raise_for_status()
		return r.json()


