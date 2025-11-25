from domain.state import AgentState
from domain.composer import build_answer_prompt
from clients.model_adapter import llm_generate

FALLBACK_NO_CONTEXT = "Xin lỗi, tôi không tìm thấy đủ thông tin trong ngữ cảnh được cung cấp."


async def node_answer(state: AgentState) -> AgentState:
	q = state.redacted_query or state.original_query
	ctx = [r.get("text", "") for r in state.retrieved if r.get("text")]
	if not ctx and not state.allow_external:
		state.answer = FALLBACK_NO_CONTEXT
		state.logs.append("answer: insufficient_context")
		return state
	tool_str = None
	if state.tool_result:
		if "data" in state.tool_result:
			tool_str = str(state.tool_result["data"])
		elif "error" in state.tool_result:
			tool_str = f"[TOOL_ERROR] {state.tool_result['error']}"
	prompt = build_answer_prompt(q, ctx, tool_str, allow_external=state.allow_external)
	out = await llm_generate(prompt=prompt, context="\n".join(ctx), language=state.language, model_hint="openai")
	state.answer = (out.get("output") or "").strip()
	state.used_external = bool(state.allow_external and state.plan.get("intent") == "tool" and state.tool_result)
	state.logs.append("answer: ok")
	return state


