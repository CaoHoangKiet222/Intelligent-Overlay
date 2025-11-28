from domain.state import AgentState
from services.qa_utils import generate_answer


async def node_fallback(state: AgentState) -> AgentState:
	if state.plan.get("intent") == "tool" and state.tool_result and "error" in state.tool_result:
		state.answer = await generate_answer(state, tool_result=None)
		state.logs.append("fallback: used RAG only")
	return state


