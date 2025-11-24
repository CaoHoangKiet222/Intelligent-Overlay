import os
from typing import Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import httpx
from domain.errors import TransientHTTPError

WORKER_MAX_RETRY = int(os.getenv("WORKER_MAX_RETRY", "2"))
MODEL_ADAPTER = os.getenv("MODEL_ADAPTER_BASE_URL", "http://model-adapter:8000")


@retry(
	stop=stop_after_attempt(WORKER_MAX_RETRY),
	wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
	retry=retry_if_exception_type(TransientHTTPError),
)
async def call_llm_generate(
	*,
	task: str,
	prompt_ref: str,
	variables: Dict[str, Any],
	language: str,
	provider_hint: str | None = None,
	context_len: int | None = None,
) -> Dict[str, Any]:
	body: Dict[str, Any] = {
		"prompt_ref": prompt_ref,
		"variables": variables,
		"language": language,
		"task": task,
	}
	if provider_hint:
		body["provider_hint"] = provider_hint
	if context_len:
		body["context_len"] = context_len
	try:
		async with httpx.AsyncClient(timeout=30.0) as client:
			r = await client.post(f"{MODEL_ADAPTER}/model/generate", json=body)
			if r.status_code >= 500:
				raise TransientHTTPError(f"Upstream 5xx: {r.text}")
			r.raise_for_status()
			return r.json()
	except httpx.TimeoutException as e:
		raise TransientHTTPError(f"Timeout: {e}") from e


