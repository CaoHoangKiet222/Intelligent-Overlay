from ...domain.state import AgentState
from ...clients.retrieval_service import hybrid_search


async def node_retrieval(state: AgentState) -> AgentState:
	q = state.redacted_query or state.original_query
	res = await hybrid_search(q, top_k=6)
	state.retrieved = res.get("results", [])
	state.citations = [{"segment_id": r["segment_id"], "score": r["scores"]["hybrid"]} for r in state.retrieved]
	state.logs.append(f"retrieval: k={len(state.retrieved)}")
	return state


