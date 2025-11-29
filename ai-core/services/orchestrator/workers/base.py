from typing import Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import httpx
from domain.errors import TransientHTTPError
from app.config import WORKER_MAX_RETRY, MODEL_ADAPTER_BASE_URL
from shared.config.base import get_base_config

MODEL_ADAPTER = MODEL_ADAPTER_BASE_URL


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
		timeout_config = get_base_config().timeout_config
		timeout = timeout_config.http_model_adapter.to_httpx_simple_timeout()
		async with httpx.AsyncClient(timeout=timeout) as client:
			r = await client.post(f"{MODEL_ADAPTER}/model/generate", json=body)
			if r.status_code >= 500:
				raise TransientHTTPError(f"Upstream 5xx: {r.text}")
			r.raise_for_status()
			return r.json()
	except httpx.TimeoutException as e:
		raise TransientHTTPError(f"Timeout: {e}") from e


