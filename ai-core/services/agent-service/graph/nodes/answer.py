from ...domain.state import AgentState
from ...domain.composer import build_answer_prompt
from ...clients.model_adapter import llm_generate


async def node_answer(state: AgentState) -> AgentState:
	q = state.redacted_query or state.original_query
	ctx = [r["text_preview"] for r in state.retrieved]
	tool_str = None
	if state.tool_result:
		if "data" in state.tool_result:
			tool_str = str(state.tool_result["data"])
		elif "error" in state.tool_result:
			tool_str = f"[TOOL_ERROR] {state.tool_result['error']}"
	prompt = build_answer_prompt(q, ctx, tool_str)
	out = await llm_generate(prompt=prompt, context="\n".join(ctx), language=state.language, model_hint="openai")
	state.answer = (out.get("output") or "").strip()
	state.logs.append("answer: ok")
	return state


