from __future__ import annotations

import logging
from typing import Dict, Any
import httpx
from shared.contracts import SpanRef


logger = logging.getLogger(__name__)


class AgentServiceClient:
	def __init__(self, base_url: str, timeout: float = 30.0):
		self._base_url = base_url.rstrip("/")
		self._timeout = timeout

	async def qa(self, context_id: str, query: str, conversation_id: str | None = None, language: str | None = None, allow_external: bool = False) -> Dict[str, Any]:
		payload = {
			"context_id": context_id,
			"query": query,
			"language": language or "auto",
			"allow_external": allow_external,
		}
		if conversation_id:
			payload["conversation_id"] = conversation_id
		
		url = f"{self._base_url}/agent/qa"
		try:
			async with httpx.AsyncClient(timeout=self._timeout) as client:
				resp = await client.post(url, json=payload)
				resp.raise_for_status()
				body = resp.json()
				return body
		except httpx.HTTPStatusError as exc:
			response_text = exc.response.text if exc.response else "No response text"
			logger.error(
				"HTTP error calling agent-service",
				extra={
					"error_type": type(exc).__name__,
					"status_code": exc.response.status_code if exc.response else None,
					"request_url": url,
					"response_text": response_text[:500],
					"context_id": context_id,
				},
				exc_info=True,
			)
			raise
		except httpx.RequestError as exc:
			logger.error(
				"Request error calling agent-service",
				extra={
					"error_type": type(exc).__name__,
					"error_message": str(exc),
					"request_url": url,
					"context_id": context_id,
				},
				exc_info=True,
			)
			raise
		except Exception as exc:
			logger.error(
				"Unexpected error calling agent-service",
				extra={
					"error_type": type(exc).__name__,
					"error_message": str(exc),
					"context_id": context_id,
				},
				exc_info=True,
			)
			raise

