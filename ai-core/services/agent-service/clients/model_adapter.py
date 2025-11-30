import os
from typing import Dict, Any, Optional

import httpx
from shared.config.base import get_base_config

BASE = os.getenv("MODEL_ADAPTER_BASE_URL", "http://model-adapter:8000").rstrip("/")


async def llm_generate(
	*,
	prompt_ref: str | None = None,
	variables: Dict[str, Any] | None = None,
	language: str = "auto",
	task: str = "default",
	model_hint: Optional[str] = None,
	prompt: str | None = None,
	context: str | None = None,
) -> Dict[str, Any]:
	timeout_config = get_base_config().timeout_config
	timeout = timeout_config.http_model_adapter.to_httpx_timeout()
	try:
		async with httpx.AsyncClient(timeout=timeout) as client:
			if prompt_ref:
				payload: Dict[str, Any] = {
					"prompt_ref": prompt_ref,
					"variables": variables or {},
					"language": language,
					"task": task,
				}
				if model_hint:
					payload["provider_hint"] = model_hint
				r = await client.post(f"{BASE}/model/generate", json=payload)
			else:
				payload = {
					"prompt": prompt or "",
					"language": language,
					"provider_hint": model_hint,
				}
				if context is not None:
					payload["context"] = context
				r = await client.post(f"{BASE}/generate", json=payload)
			r.raise_for_status()
			return r.json()
	except (httpx.ReadTimeout, httpx.TimeoutException, httpx.ConnectTimeout) as e:
		raise TimeoutError(f"model_adapter_timeout: {type(e).__name__}: {str(e)}") from e


