from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, Any, List
from httpx import HTTPStatusError
from jinja2 import Template
from clients.prompt_service import PromptServiceClient


@dataclass
class PromptDefinition:
	key: str
	name: str
	description: str
	template: str
	variables: Dict[str, Any]
	tags: List[str] | None = None


DEFAULT_PROMPTS: List[PromptDefinition] = [
	PromptDefinition(
		key="demo.summary.v1",
		name="Demo Summary Prompt",
		description="Dual-phase summary -> bullet list with seg citations",
		variables={"required": ["context"], "optional": ["instructions"]},
		template=(
			"You are an expert analyst. Read the context below where each paragraph is prefixed with "
			"a segment marker such as [seg:UUID].\n"
			"Context:\n{{ context }}\n\n"
			"Task:\n"
			"- Generate 3 concise bullets (<=18 words each).\n"
			"- Each bullet MUST include at least one segment marker using the exact [seg:UUID] token.\n"
			"- Do not fabricate markers.\n"
			"{% if instructions %}Additional instructions: {{ instructions }}{% endif %}\n"
			"Return plain text with each bullet on its own line prefixed by '- '."
		),
	),
	PromptDefinition(
		key="demo.argument.v1",
		name="Demo Argument Prompt",
		description="Claim/Evidence/Reasoning extraction with segment refs",
		variables={"required": ["context"], "optional": []},
		template=(
			"Analyze the context below (segment markers provided) and output three lines EXACTLY:\n"
			"CLAIM: <short claim with [seg:UUID] markers>\n"
			"EVIDENCE: <evidence summary with [seg:UUID] markers>\n"
			"REASONING: <logical bridge, cite segments when relevant>\n"
			"Context:\n{{ context }}"
		),
	),
	PromptDefinition(
		key="demo.implication.v1",
		name="Demo Implication & Sentiment Prompt",
		description="Implications plus sentiment classification",
		variables={"required": ["context"], "optional": []},
		template=(
			"Read the context with segment markers.\n"
			"Output format:\n"
			"IMPLICATIONS:\n"
			"1. text ... [seg:UUID]\n"
			"2. ... (up to 2 items)\n"
			"SENTIMENT: <positive|neutral|negative|mixed> - explanation with [seg:UUID]\n"
			"Context:\n{{ context }}"
		),
	),
	PromptDefinition(
		key="demo.logic_bias.v1",
		name="Demo Logic/Bias Prompt",
		description="Find fallacies/bias with severity",
		variables={"required": ["context"], "optional": []},
		template=(
			"Scan the context (segment markers provided) for logic issues or bias.\n"
			"Return up to 2 findings, each on its own line as:\n"
			"ISSUE: <type>; SEG: seg:<UUID>; SEVERITY: <1-3>; NOTE: <explanation>\n"
			"Context:\n{{ context }}"
		),
	),
	PromptDefinition(
		key="demo.qa.v1",
		name="Demo QA Prompt",
		description="Strict RAG QA answer",
		variables={"required": ["context", "question"], "optional": []},
		template=(
			"You are a helpful assistant. Only answer using the provided context.\n"
			"Context chunks include segment markers [seg:UUID].\n"
			"Question: {{ question }}\n"
			"Respond with:\n"
			"ANSWER: <text>\n"
			"CITATIONS: seg:UUID, seg:UUID (list all used markers)\n"
			"CONFIDENCE: <0-1 number>"
			"\nContext:\n{{ context }}"
		),
	),
]


class PromptBootstrapper:
	def __init__(self, client: PromptServiceClient):
		self._client = client

	async def ensure_prompts(self, definitions: List[PromptDefinition]) -> None:
		for definition in definitions:
			await self._ensure_single(definition)

	async def _ensure_single(self, definition: PromptDefinition) -> None:
		try:
			current = await self._client.get_prompt_by_key(definition.key)
		except HTTPStatusError as exc:
			if exc.response.status_code != 404:
				raise
			prompt_id = await self._client.create_prompt(
				{
					"key": definition.key,
					"name": definition.name,
					"description": definition.description,
					"tags": definition.tags,
				}
			)
			await self._client.create_version(prompt_id, {"template": definition.template, "variables": definition.variables})
			return

		prompt_id = current["prompt"]["id"]
		current_template = (current["version"]["template"] or "").strip()
		if current_template != definition.template.strip():
			await self._client.create_version(prompt_id, {"template": definition.template, "variables": definition.variables})


class PromptProvider:
	def __init__(self, client: PromptServiceClient, cache_ttl_sec: int = 300):
		self._client = client
		self._ttl = cache_ttl_sec
		self._cache: Dict[str, tuple[float, Dict[str, Any]]] = {}

	async def _get_prompt(self, key: str) -> Dict[str, Any]:
		now = time.monotonic()
		cached = self._cache.get(key)
		if cached and cached[0] > now:
			return cached[1]
		data = await self._client.get_prompt_by_key(key)
		self._cache[key] = (now + self._ttl, data)
		return data

	async def render(self, key: str, **variables: Any) -> str:
		prompt_payload = await self._get_prompt(key)
		template = Template(prompt_payload["version"]["template"])
		return template.render(**variables)

