import os, httpx
from typing import Dict, Any

BASE = os.getenv("BACKEND_BASE_URL", "http://backend:8080")


async def get_order_status(order_id: str) -> Dict[str, Any]:
	async with httpx.AsyncClient(timeout=15.0) as client:
		r = await client.get(f"{BASE}/orders/{order_id}")
		r.raise_for_status()
		return r.json()


async def get_refund_policy() -> Dict[str, Any]:
	async with httpx.AsyncClient(timeout=10.0) as client:
		r = await client.get(f"{BASE}/policy/refund")
		r.raise_for_status()
		return r.json()


