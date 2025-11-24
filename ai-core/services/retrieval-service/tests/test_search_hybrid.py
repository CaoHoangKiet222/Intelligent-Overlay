import types
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_retrieval_hybrid(monkeypatch):
	from clients import model_adapter as ma
	from data import repositories as repo
	from routers import search as search_router

	async def fake_embed(texts):
		return {"vectors": [[0.0, 0.1, 0.2] for _ in texts], "model": "stub", "dim": 3}

	class FakeSession:
		async def __aenter__(self):
			return self

		async def __aexit__(self, *args):
			return False

	def fake_session_local():
		return FakeSession()

	async def fake_run_hybrid(session, context_id, payload, qvec):
		return [
			{
				"id": "seg-1",
				"document_id": context_id,
				"text": "hello world segment",
				"start_offset": 0,
				"end_offset": 20,
				"sentence_no": 0,
				"score": 0.9,
				"breakdown": {"vector": 0.8, "lexical": 0.7},
			}
		]

	monkeypatch.setattr(ma, "embed_texts", fake_embed)
	monkeypatch.setattr(repo, "get_document_by_id", lambda *args, **kwargs: types.SimpleNamespace(id=kwargs["document_id"]))
	monkeypatch.setattr(search_router, "SessionLocal", fake_session_local)
	monkeypatch.setattr(search_router, "_run_hybrid", fake_run_hybrid)

	context_id = "00000000-0000-0000-0000-000000000001"
	res = client.post(
		"/retrieval/search",
		json={"context_id": context_id, "query": "hello world", "top_k": 3, "mode": "hybrid"},
	)
	assert res.status_code == 200
	body = res.json()
	assert body["context_id"] == context_id
	assert body["results"]
	first = body["results"][0]
	assert first["span"]["segment_id"] == "seg-1"
	assert first["breakdown"]["vector"] == 0.8
	assert "snippet" in first
