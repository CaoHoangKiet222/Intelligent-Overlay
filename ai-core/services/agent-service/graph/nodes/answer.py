from domain.state import AgentState
from services.qa_utils import generate_answer

FALLBACK_NO_CONTEXT = "Xin lỗi, tôi không tìm thấy đủ thông tin trong ngữ cảnh được cung cấp."


async def node_answer(state: AgentState) -> AgentState:
	q = state.redacted_query or state.original_query
	# Extract text from retrieval results - check snippet first, then span.text_preview, then text
	ctx = []
	for r in state.retrieved:
		text = r.get("snippet") or ""
		if not text:
			span = r.get("span")
			if isinstance(span, dict):
				text = span.get("text_preview") or span.get("text") or ""
			elif hasattr(span, "text_preview"):
				text = span.text_preview or ""
		if not text:
			text = r.get("text") or ""
		if text:
			ctx.append(text)
	
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
	state.answer = await generate_answer(state, tool_str)
	state.used_external = bool(state.allow_external and state.plan.get("intent") == "tool" and state.tool_result)
	state.logs.append("answer: ok")
	return state


