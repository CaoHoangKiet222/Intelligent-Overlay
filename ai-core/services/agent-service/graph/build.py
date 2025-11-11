from langgraph.graph import StateGraph, END
from ..domain.state import AgentState
from .nodes.policy_guard import node_policy_guard
from .nodes.intake import node_intake
from .nodes.retrieval import node_retrieval
from .nodes.planner_node import node_planner
from .nodes.tool_call import node_tool_call
from .nodes.answer import node_answer
from .nodes.fallback import node_fallback


def build_graph():
	g = StateGraph(AgentState)
	g.add_node("policy_guard", node_policy_guard)
	g.add_node("intake", node_intake)
	g.add_node("retrieval", node_retrieval)
	g.add_node("planner", node_planner)
	g.add_node("tool_call", node_tool_call)
	g.add_node("answer", node_answer)
	g.add_node("fallback", node_fallback)
	g.set_entry_point("policy_guard")
	g.add_edge("policy_guard", "intake")
	g.add_edge("intake", "retrieval")
	g.add_edge("retrieval", "planner")
	g.add_edge("planner", "tool_call")
	g.add_edge("tool_call", "answer")
	g.add_edge("answer", "fallback")
	g.add_edge("fallback", END)
	return g.compile()


