import pytest
from fastapi.testclient import TestClient
from app import app


client = TestClient(app)


@pytest.mark.parametrize("text", ["Hello world. This is a long text. " * 50])
def test_ingest_text_ok(monkeypatch, text):
	# stub embed_texts
	from clients import model_adapter as ma
	async def fake_embed(texts):
		return {"vectors": [[0.1, 0.2, 0.3] for _ in texts], "model": "stub", "dim": 3}
	monkeypatch.setattr(ma, "embed_texts", fake_embed)

	# stub DB ops to no-op
	from data import repositories as repo
	async def fake_create_document(s, payload):
		class D:
			id = "00000000-0000-0000-0000-000000000001"
		return D()
	async def fake_bulk_segments(s, doc_id, items):
		class S:
			def __init__(self, i): self.id = f"seg-{i}"
		return [S(i) for i in range(len(items))]
	async def fake_bulk_embeddings(s, pairs):
		return None
	monkeypatch.setattr(repo, "create_document", fake_create_document)
	monkeypatch.setattr(repo, "bulk_insert_segments", fake_bulk_segments)
	monkeypatch.setattr(repo, "bulk_insert_embeddings", fake_bulk_embeddings)

	res = client.post("/ingest", data={"source_type": "text", "text": text})
	assert res.status_code == 200
	body = res.json()
	assert body["segments_created"] > 1
	assert body["dim"] == 3


