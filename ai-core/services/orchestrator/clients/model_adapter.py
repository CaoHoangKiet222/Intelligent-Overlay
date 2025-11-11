import httpx
import os

MODEL_ADAPTER_BASE_URL = os.getenv("MODEL_ADAPTER_BASE_URL", "http://model-adapter:8000")

async def generate(payload: dict) -> dict:
	async with httpx.AsyncClient(timeout=30.0) as client:
		r = await client.post(f"{MODEL_ADAPTER_BASE_URL}/generate", json=payload)
		r.raise_for_status()
		return r.json()


