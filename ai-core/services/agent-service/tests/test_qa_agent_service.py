import pytest
from domain.schemas import QaRequest
from services.qa_agent import QaAgentService
from shared.contracts import SpanRef


async def fake_retrieval_fn(context_id: str, query: str, top_k: int):
	return {
		"results": [
			{
				"span": SpanRef(segment_id="seg-1", text_preview="A").model_dump(by_alias=True),
				"snippet": "Latency giảm 20%",
				"score": 0.82,
			}
		]
	}


async def fake_llm_fn(prompt_ref: str, variables, language: str, task: str, model_hint: str):
	return {"output": "Caching tầng edge giúp giảm độ trễ [#citation_1]"}


@pytest.mark.asyncio
async def test_qa_agent_returns_answer_with_citations():
	service = QaAgentService(
		retrieval_fn=fake_retrieval_fn,
		llm_fn=fake_llm_fn,
	)
	req = QaRequest(context_id="ctx-123", query="Vì sao latency giảm?")
	resp = await service.answer(req)
	assert resp.answer.startswith("Caching")
	assert resp.citations and resp.citations[0].chunk_id == "seg-1"
	assert 0.5 <= resp.confidence <= 0.95

