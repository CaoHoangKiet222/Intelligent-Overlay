from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def _mock_retrieval(monkeypatch):
	from clients import retrieval_service as rs

	async def fake_search(query: str, top_k: int = 6):
		return {
			"results": [
				{
					"segment_id": "s1",
					"text": "hello world",
					"scores": {"hybrid": 0.9},
					"span": {"segment_id": "s1", "start_offset": 0, "end_offset": 5},
				}
			]
		}

	async def fake_search_context(context_id: str, query: str, top_k: int = 5, mode: str = "hybrid"):
		return await fake_search(query, top_k)

	monkeypatch.setattr(rs, "hybrid_search", fake_search)
	monkeypatch.setattr(rs, "search_context_spans", fake_search_context)


def _mock_llm(monkeypatch):
	from clients import model_adapter as ma

	async def fake_generate(**kwargs):
		return {"output": "demo answer"}

	monkeypatch.setattr(ma, "llm_generate", fake_generate)


def test_ask_basic(monkeypatch):
	_mock_retrieval(monkeypatch)
	_mock_llm(monkeypatch)
	r = client.post("/agent/ask", json={"query": "Xin chào", "language": "vi"})
	assert r.status_code == 200
	body = r.json()
	assert "answer" in body
	assert isinstance(body["logs"], list)


def test_agent_qa_route(monkeypatch):
	_mock_retrieval(monkeypatch)
	_mock_llm(monkeypatch)
	r = client.post(
		"/agent/qa",
		json={
			"context_id": "ctx-1",
			"query": "Xin chào",
			"conversation_id": "conv-1",
			"allow_external": False,
		},
	)
	assert r.status_code == 200
	body = r.json()
	assert body["conversation_id"] == "conv-1"
	assert "confidence" in body
	assert isinstance(body["citations"], list)


