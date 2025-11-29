import os, httpx
from typing import Dict, Any
from shared.config.base import get_base_config

BASE = os.getenv("BACKEND_BASE_URL", "http://backend:8080")


async def get_order_status(order_id: str) -> Dict[str, Any]:
	timeout_config = get_base_config().timeout_config
	timeout = timeout_config.http_default.to_httpx_simple_timeout()
	async with httpx.AsyncClient(timeout=timeout) as client:
		r = await client.get(f"{BASE}/orders/{order_id}")
		r.raise_for_status()
		return r.json()


async def get_refund_policy() -> Dict[str, Any]:
	timeout_config = get_base_config().timeout_config
	timeout = timeout_config.http_default.to_httpx_simple_timeout()
	async with httpx.AsyncClient(timeout=timeout) as client:
		r = await client.get(f"{BASE}/policy/refund")
		r.raise_for_status()
		return r.json()


