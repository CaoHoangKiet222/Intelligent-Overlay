from __future__ import annotations

from typing import Dict, Tuple

import httpx


class PromptServiceClient:
	def __init__(self, base_url: str, timeout: float = 15.0):
		self._base_url = base_url.rstrip("/")
		self._timeout = timeout

	async def fetch_prompt(self, prompt_ref: str) -> Tuple[str, Dict[str, object]]:
		async with httpx.AsyncClient(timeout=self._timeout) as client:
			resp = await client.get(f"{self._base_url}/prompts/{prompt_ref}")
			resp.raise_for_status()
			body = resp.json()
			version = body.get("version") or {}
			return version.get("template", "") or "", version.get("variables") or {}

