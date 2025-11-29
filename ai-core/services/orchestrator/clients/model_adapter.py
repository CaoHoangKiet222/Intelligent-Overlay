import httpx
from app.config import MODEL_ADAPTER_BASE_URL
from shared.config.base import get_base_config

async def generate(payload: dict) -> dict:
	timeout_config = get_base_config().timeout_config
	timeout = timeout_config.http_model_adapter.to_httpx_simple_timeout()
	async with httpx.AsyncClient(timeout=timeout) as client:
		r = await client.post(f"{MODEL_ADAPTER_BASE_URL}/generate", json=payload)
		r.raise_for_status()
		return r.json()


