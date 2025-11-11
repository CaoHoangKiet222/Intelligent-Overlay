import json
from ...domain.state import AgentState
from ...domain.planner import build_planner_prompt
from ...clients.model_adapter import llm_generate


async def node_planner(state: AgentState) -> AgentState:
	q = state.redacted_query or state.original_query
	ctx = [r["text_preview"] for r in state.retrieved]
	prompt = build_planner_prompt(q, ctx)
	out = await llm_generate(prompt=prompt, context="\n".join(ctx), language=state.language, model_hint="openai")
	txt = (out.get("output") or "").strip()
	try:
		plan = json.loads(txt)
	except Exception:
		plan = {"intent": "qa_only"}
	state.plan = plan
	state.logs.append(f"planner: {plan}")
	return state


