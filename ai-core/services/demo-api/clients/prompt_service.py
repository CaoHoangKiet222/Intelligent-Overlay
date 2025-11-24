from typing import Dict, Any, Optional
import httpx


class PromptServiceClient:
	def __init__(self, base_url: str, timeout: float = 15.0):
		self._base_url = base_url.rstrip("/")
		self._timeout = timeout

	async def get_prompt_by_key(self, key: str, version: Optional[int] = None) -> Dict[str, Any]:
		params = {"version": version} if version is not None else None
		async with httpx.AsyncClient(timeout=self._timeout) as client:
			resp = await client.get(f"{self._base_url}/prompts/by-key/{key}", params=params)
			resp.raise_for_status()
			return resp.json()

	async def create_prompt(self, payload: Dict[str, Any]) -> str:
		async with httpx.AsyncClient(timeout=self._timeout) as client:
			resp = await client.post(f"{self._base_url}/prompts", json=payload)
			resp.raise_for_status()
			body = resp.json()
			return body["id"]

	async def create_version(self, prompt_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
		async with httpx.AsyncClient(timeout=self._timeout) as client:
			resp = await client.post(f"{self._base_url}/prompts/{prompt_id}/versions", json=payload)
			resp.raise_for_status()
			return resp.json()

