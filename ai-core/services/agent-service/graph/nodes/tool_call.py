from domain.state import AgentState
from tools.registry import REGISTRY


async def node_tool_call(state: AgentState) -> AgentState:
	plan = state.plan or {}
	if plan.get("intent") != "tool":
		state.logs.append("tool_call: skipped")
		return state
	if not state.allow_external:
		state.logs.append("tool_call: blocked_by_policy")
		return state
	tool = plan.get("tool")
	fn = REGISTRY.get(tool or "")
	if not fn:
		state.logs.append(f"tool_call: unknown tool {tool}")
		return state
	args = plan.get("args") or {}
	try:
		result = await fn(**args)
		state.tool_result = {"tool": tool, "data": result}
		state.used_external = True
		state.logs.append(f"tool_call: ok {tool}")
		return state
	except Exception as e:
		state.tool_result = {"tool": tool, "error": str(e)}
		state.logs.append(f"tool_call: error {tool}: {e}")
		return state


