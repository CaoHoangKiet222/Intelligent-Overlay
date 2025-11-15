import pytest
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_search_basic(monkeypatch):
	# stub embed_texts
	from clients import model_adapter as ma
	async def fake_embed(texts):
		return {"vectors": [[0.0, 0.0, 1.0] for _ in texts], "model": "stub", "dim": 3}
	monkeypatch.setattr(ma, "embed_texts", fake_embed)

	# stub DB execute to return fake rows
	from data import db as dbmod
	class FakeRes:
		def mappings(self):
			class C:
				def all(self_inner):
					return [
						{"id": "seg-1", "document_id": "doc-1", "text": "hello world", "start_offset": 0, "end_offset": 11, "page_no": None, "paragraph_no": None, "sentence_no": None, "vscore": 0.9, "tscore": 0.8, "hybrid": 0.86},
						{"id": "seg-2", "document_id": "doc-1", "text": "another text", "start_offset": 12, "end_offset": 24, "page_no": None, "paragraph_no": None, "sentence_no": None, "vscore": 0.7, "tscore": 0.6, "hybrid": 0.67},
					]
			return C()
	class FakeSession:
		async def __aenter__(self): return self
		async def __aexit__(self, *args): return False
		async def execute(self, *args, **kwargs): return FakeRes()
	def fake_session_local(): return FakeSession()
	dbmod.SessionLocal = fake_session_local

	res = client.post("/search", json={"query": "hello world"})
	assert res.status_code == 200
	body = res.json()
	assert body["took_ms"] >= 0
	assert len(body["results"]) >= 1
	assert "scores" in body["results"][0]


