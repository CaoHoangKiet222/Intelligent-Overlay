from domain.state import AgentState
from domain.composer import build_answer_prompt
from clients.model_adapter import llm_generate


async def node_fallback(state: AgentState) -> AgentState:
	if state.plan.get("intent") == "tool" and state.tool_result and "error" in state.tool_result:
		q = state.redacted_query or state.original_query
		ctx = [r.get("text", "") for r in state.retrieved if r.get("text")]
		prompt = build_answer_prompt(q, ctx, tool_result=None, allow_external=state.allow_external)
		out = await llm_generate(prompt=prompt, context="\n".join(ctx), language=state.language, model_hint="openai")
		state.answer = (out.get("output") or "").strip()
		state.logs.append("fallback: used RAG only")
	return state


