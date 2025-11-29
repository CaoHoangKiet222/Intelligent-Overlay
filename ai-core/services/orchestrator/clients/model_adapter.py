import httpx
from app.config import MODEL_ADAPTER_BASE_URL

async def generate(payload: dict) -> dict:
	async with httpx.AsyncClient(timeout=30.0) as client:
		r = await client.post(f"{MODEL_ADAPTER_BASE_URL}/generate", json=payload)
		r.raise_for_status()
		return r.json()


