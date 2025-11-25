from domain.state import AgentState
from clients.retrieval_service import hybrid_search, search_context_spans
from shared.contracts import SpanRef


async def node_retrieval(state: AgentState) -> AgentState:
	q = state.redacted_query or state.original_query
	if state.context_id:
		res = await search_context_spans(state.context_id, q, top_k=6)
	else:
		res = await hybrid_search(q, top_k=6)
	state.retrieved = res.get("results", [])
	state.citations = []
	for item in state.retrieved:
		span_payload = item.get("span")
		if span_payload:
			state.citations.append(SpanRef.model_validate(span_payload))
		else:
			state.citations.append(
				SpanRef(
					segment_id=item["segment_id"],
					start_offset=item.get("start_offset"),
					end_offset=item.get("end_offset"),
					text_preview=(item.get("text") or "")[:200],
					score=(item.get("scores") or {}).get("hybrid"),
				)
			)
	state.logs.append(f"retrieval: k={len(state.retrieved)}")
	return state


