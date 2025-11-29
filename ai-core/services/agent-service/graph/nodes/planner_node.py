import json
from domain.state import AgentState
from domain.planner import build_planner_prompt
from clients.model_adapter import llm_generate
from app.config import AgentConfig

_config = AgentConfig.from_env()


async def node_planner(state: AgentState) -> AgentState:
	q = state.redacted_query or state.original_query
	ctx = [r.get("text", "") for r in state.retrieved if r.get("text")]
	prompt = build_planner_prompt(q, ctx, allow_external=state.allow_external)
	out = await llm_generate(prompt=prompt, context="\n".join(ctx), language=state.language, model_hint=_config.planner_model_hint)
	txt = (out.get("output") or "").strip()
	try:
		plan = json.loads(txt)
	except Exception:
		plan = {"intent": "qa_only"}
	if not state.allow_external and plan.get("intent") == "tool":
		plan = {"intent": "qa_only", "reason": "external_disabled"}
	state.plan = plan
	state.logs.append(f"planner: {plan}")
	return state


