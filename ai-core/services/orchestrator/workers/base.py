import os
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import httpx
from domain.errors import TransientHTTPError

WORKER_MAX_RETRY = int(os.getenv("WORKER_MAX_RETRY", "2"))
MODEL_ADAPTER = os.getenv("MODEL_ADAPTER_BASE_URL", "http://model-adapter:8000")
PROMPT_SVC = os.getenv("PROMPT_SERVICE_BASE_URL", "http://prompt-service:8000")


async def fetch_prompt(prompt_id: str):
	async with httpx.AsyncClient(timeout=15.0) as client:
		r = await client.get(f"{PROMPT_SVC}/prompts/{prompt_id}")
		r.raise_for_status()
		body = r.json()
		return body["version"]["template"], body["version"]["variables"]


@retry(
	stop=stop_after_attempt(WORKER_MAX_RETRY),
	wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
	retry=retry_if_exception_type(TransientHTTPError),
)
async def call_llm_generate(model_hint: str, prompt: str, context: str, language: str):
	try:
		async with httpx.AsyncClient(timeout=30.0) as client:
			r = await client.post(
				f"{MODEL_ADAPTER}/generate",
				json={
					"prompt": prompt,
					"language": language,
					"provider_hint": model_hint,
				},
			)
			if r.status_code >= 500:
				raise TransientHTTPError(f"Upstream 5xx: {r.text}")
			r.raise_for_status()
			return r.json()
	except httpx.TimeoutException as e:
		raise TransientHTTPError(f"Timeout: {e}") from e


