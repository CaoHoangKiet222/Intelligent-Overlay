from domain.state import AgentState


async def node_intake(state: AgentState) -> AgentState:
	q = state.redacted_query or state.original_query
	state.logs.append(f"intake: lang={state.language}, q_len={len(q)}")
	return state


