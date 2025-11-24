import httpx


class ModelAdapterClient:
	def __init__(self, base_url: str, timeout: float = 30.0):
		self._base_url = base_url.rstrip("/")
		self._timeout = timeout

	async def generate(self, prompt: str, language: str | None, provider_hint: str | None = None) -> dict:
		payload = {
			"prompt": prompt,
			"language": language,
			"provider_hint": provider_hint,
		}
		async with httpx.AsyncClient(timeout=self._timeout) as client:
			resp = await client.post(f"{self._base_url}/generate", json=payload)
			resp.raise_for_status()
			return resp.json()

