import pytest
from shared.contracts import ContextChunk
from workers import summary_worker


@pytest.mark.asyncio
async def test_summary_worker_returns_bullet_with_span(monkeypatch):
	async def fake_llm_call(**_kwargs):
		return {"output": "- Key insight [seg:chunk-001]"}

	monkeypatch.setattr(summary_worker, "call_llm_generate", fake_llm_call)

	segments = [
		ContextChunk(
			chunk_id="chunk-001",
			text="The Intelligent Overlay pilot shows latency improvements with caching layers and resilient routing.",
		),
		ContextChunk(
			chunk_id="chunk-002",
			text="User feedback also highlights clearer dashboards and faster alerting workflows across regions.",
		),
	]

	payload, _ = await summary_worker.summarize_context(
		context_id="ctx-123",
		language="en",
		prompt_ref="key:test.summary",
		segments=segments,
	)

	assert payload.bullets, "Summary worker should return at least one bullet"
	first_bullet = payload.bullets[0]
	assert first_bullet.spans, "Bullet must include a SpanRef citation"
	assert first_bullet.spans[0].chunk_id == "chunk-001"

