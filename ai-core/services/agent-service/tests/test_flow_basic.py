from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_ask_basic(monkeypatch):
	# stub external calls to be fast
	from clients import retrieval_service as rs
	async def fake_search(query: str, top_k: int = 6):
		return {"results": [{"segment_id": "s1", "text_preview": "hello world", "scores": {"hybrid": 0.9}}]}
	monkeypatch.setattr(rs, "hybrid_search", fake_search)

	from clients import model_adapter as ma
	async def fake_generate(prompt: str, context: str, language: str, model_hint=None):
		return {"output": "demo answer"}
	monkeypatch.setattr(ma, "llm_generate", fake_generate)

	r = client.post("/agent/ask", json={"query": "Xin chào", "language": "vi"})
	assert r.status_code == 200
	body = r.json()
	assert "answer" in body
	assert isinstance(body["logs"], list)


