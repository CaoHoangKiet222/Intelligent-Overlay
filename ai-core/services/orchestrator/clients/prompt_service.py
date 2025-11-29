import httpx
from app.config import PROMPT_SERVICE_BASE_URL

async def get_prompt(prompt_id: str) -> dict:
	async with httpx.AsyncClient(timeout=15.0) as client:
		r = await client.get(f"{PROMPT_SERVICE_BASE_URL}/prompts/{prompt_id}")
		r.raise_for_status()
		return r.json()


