from __future__ import annotations

import re
from typing import Dict, Tuple

from clients.prompt_service import PromptServiceClient

PLACEHOLDER = re.compile(r"{{\s*([a-zA-Z0-9_\.]+)\s*}}")


class PromptRenderer:
	def __init__(self, client: PromptServiceClient):
		self._client = client

	async def render(self, prompt_ref: str, variables: Dict[str, object]) -> Tuple[str, Dict[str, object]]:
		template, meta = await self._client.fetch_prompt(prompt_ref)
		rendered = PLACEHOLDER.sub(lambda m: str(variables.get(m.group(1), "")), template)
		return rendered.strip(), meta

