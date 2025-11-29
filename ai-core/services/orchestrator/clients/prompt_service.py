import httpx
from app.config import PROMPT_SERVICE_BASE_URL
from shared.config.base import get_base_config

async def get_prompt(prompt_id: str) -> dict:
	timeout_config = get_base_config().timeout_config
	timeout = timeout_config.http_prompt_service.to_httpx_simple_timeout()
	async with httpx.AsyncClient(timeout=timeout) as client:
		r = await client.get(f"{PROMPT_SERVICE_BASE_URL}/prompts/{prompt_id}")
		r.raise_for_status()
		return r.json()


