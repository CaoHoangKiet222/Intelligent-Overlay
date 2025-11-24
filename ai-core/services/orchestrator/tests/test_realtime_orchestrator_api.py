from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from domain.schemas import (
	ArgumentClaim,
	ArgumentWorkerOutput,
	ImplicationItem,
	ImplicationSentimentOutput,
	LogicBiasFinding,
	LogicBiasOutput,
	SentimentResult,
	SummaryWorkerBullet,
	SummaryWorkerOutput,
)
from routers.orchestrators import router as orchestrator_router
from shared.contracts import ContextChunk, SpanRef


@pytest.fixture()
def test_app(monkeypatch):
	app = FastAPI()
	app.include_router(orchestrator_router)

	async def fake_summary(**_kwargs):
		payload = SummaryWorkerOutput(
			context_id="ctx-1",
			bullets=[
				SummaryWorkerBullet(
					bullet="Tổng quan demo",
					spans=[SpanRef(segment_id="seg-1")],
				)
			],
		)
		return payload, {"fake": True}

	async def fake_argument(**_kwargs):
		payload = ArgumentWorkerOutput(
			context_id="ctx-1",
			claims=[
				ArgumentClaim(
					claim="Claim chính",
					evidence_spans=[SpanRef(segment_id="seg-1")],
					reasoning="Có số liệu hỗ trợ.",
					confidence=0.9,
				)
			],
		)
		return payload, {"fake": True}

	async def fake_implication(**_kwargs):
		payload = ImplicationSentimentOutput(
			context_id="ctx-1",
			implications=[
				ImplicationItem(
					text="Văn bản hàm ý cần mở rộng rollout.",
					spans=[SpanRef(segment_id="seg-1")],
					confidence=0.8,
				)
			],
			sentiment=SentimentResult(label="positive", score=0.8),
		)
		return payload, {"fake": True}

	async def fake_logic_bias(**_kwargs):
		payload = LogicBiasOutput(
			context_id="ctx-1",
			findings=[
				LogicBiasFinding(
					type="hasty_generalization",
					span=SpanRef(segment_id="seg-1"),
					explanation="Ngôn ngữ tuyệt đối.",
					severity=2,
				)
			],
		)
		return payload, {"fake": True}

	monkeypatch.setattr("routers.orchestrators.summarize_context", fake_summary)
	monkeypatch.setattr("routers.orchestrators.analyze_arguments", fake_argument)
	monkeypatch.setattr("routers.orchestrators.analyze_implication_sentiment", fake_implication)
	monkeypatch.setattr("routers.orchestrators.analyze_logic_bias", fake_logic_bias)

	return TestClient(app)


def test_realtime_orchestrator_returns_bundle(test_app):
	chunk = ContextChunk(
		chunk_id="seg-1",
		text="Demo Intelligent Overlay giảm độ trễ.",
	)
	resp = test_app.post(
		"/orchestrator/analyze",
		json={
			"context_id": "ctx-1",
			"segments": [chunk.model_dump(by_alias=True)],
		},
	)
	assert resp.status_code == 200
	body = resp.json()
	assert body["summary"]["context_id"] == "ctx-1"
	assert body["arguments"]["claims"][0]["claim"] == "Claim chính"
	assert body["implications"][0]["text"].startswith("Văn bản hàm ý")
	assert body["sentiment"]["label"] == "positive"
	assert body["logic_bias"]["findings"][0]["type"] == "hasty_generalization"
	assert body["worker_statuses"]["summary"] == "ok"

