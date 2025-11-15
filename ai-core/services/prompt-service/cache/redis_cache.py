import json
from typing import Optional, Dict, Any
import redis.asyncio as redis
from app.config import PROMPT_CACHE_TTL_SECONDS, REDIS_URL


class PromptCache:
	def __init__(self, url: str = REDIS_URL):
		self.client = redis.from_url(url, decode_responses=True)

	def key(self, prompt_id: str, version: int) -> str:
		return f"prompt:{prompt_id}:v:{version}"

	async def get(self, prompt_id: str, version: int) -> Optional[Dict[str, Any]]:
		val = await self.client.get(self.key(prompt_id, version))
		return json.loads(val) if val else None

	async def set(self, prompt_id: str, version: int, data: Dict[str, Any]) -> None:
		await self.client.set(self.key(prompt_id, version), json.dumps(data), ex=PROMPT_CACHE_TTL_SECONDS)

	async def invalidate(self, prompt_id: str, version: int) -> None:
		await self.client.delete(self.key(prompt_id, version))


