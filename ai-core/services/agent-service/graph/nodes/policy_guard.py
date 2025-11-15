from domain.state import AgentState
from domain.policies import redact_pii


async def node_policy_guard(state: AgentState) -> AgentState:
	red, flags = redact_pii(state.original_query)
	state.redacted_query = red
	state.guard_flags = flags
	state.logs.append(f"policy_guard: redacted={bool(flags)}")
	return state


