from __future__ import annotations

from typing import Sequence, Dict, Any, Optional

from clients.model_adapter import llm_generate
from domain.composer import build_answer_prompt
from domain.state import AgentState
from app.config import AgentConfig

_config = AgentConfig.from_env()


def estimate_confidence(results: Sequence[Dict[str, Any]], answer: str) -> float:
	if not results:
		return 0.3
	top_score = 0.0
	for item in results:
		score = item.get("score")
		if score is None:
			span = item.get("span") or {}
			score = span.get("score")
		if score:
			try:
				top_score = max(top_score, float(score))
			except (TypeError, ValueError):
				continue
	base = 0.55 + 0.08 * min(len(results), 3)
	if top_score:
		base += 0.1 * min(top_score, 1.0)
	lower = (answer or "").lower()
	if "không chắc" in lower or "khong chac" in lower or "does not know" in lower:
		base = min(base, 0.5)
	return round(min(0.95, base), 2)


async def generate_answer(state: AgentState, tool_result: Optional[str]) -> str:
	q = state.redacted_query or state.original_query
	ctx = [r.get("text", "") for r in state.retrieved if r.get("text")]
	prompt = build_answer_prompt(q, ctx, tool_result, allow_external=state.allow_external)
	out = await llm_generate(
		prompt=prompt,
		context="\n".join(ctx),
		language=state.language,
		model_hint=_config.answer_model_hint,
	)
	return (out.get("output") or "").strip()

