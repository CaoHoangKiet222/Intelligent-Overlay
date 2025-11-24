import pytest
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


@pytest.mark.parametrize("text", ["Hello world. This is a long text. " * 50])
def test_normalize_and_index_ok(monkeypatch, text):
	from clients import model_adapter as ma
	from data import repositories as repo
	from data import db as dbmod

	async def fake_embed(texts):
		return {"vectors": [[0.1, 0.2, 0.3] for _ in texts], "model": "stub", "dim": 3}

	class FakeDoc:
		def __init__(self):
			self.id = "00000000-0000-0000-0000-000000000001"
			self.locale = "vi"

	class FakeSegment:
		def __init__(self, idx):
			self.id = f"seg-{idx}"
			self.document_id = FakeDoc().id
			self.text = f"chunk-{idx}"
			self.start_offset = idx * 10
			self.end_offset = idx * 10 + 5
			self.page_no = None
			self.paragraph_no = None
			self.sentence_no = idx
			self.speaker_label = None
			self.timestamp_start_ms = None
			self.timestamp_end_ms = None

	class FakeSession:
		async def __aenter__(self):
			return self

		async def __aexit__(self, *args):
			return False

		def begin(self):
			class Tx:
				async def __aenter__(self_inner):
					return self_inner

				async def __aexit__(self_inner, *args):
					return False
			return Tx()

	monkeypatch.setattr(ma, "embed_texts", fake_embed)
	monkeypatch.setattr(repo, "get_document_by_hash", lambda *args, **kwargs: None)
	monkeypatch.setattr(repo, "create_document", lambda *args, **kwargs: FakeDoc())
	monkeypatch.setattr(repo, "bulk_insert_segments", lambda *args, **kwargs: [FakeSegment(i) for i in range(3)])
	monkeypatch.setattr(repo, "bulk_insert_embeddings", lambda *args, **kwargs: None)
	monkeypatch.setattr(dbmod, "SessionLocal", lambda: FakeSession())

	res = client.post("/ingestion/normalize_and_index", json={"raw_text": text, "locale": "vi", "url": None})
	assert res.status_code == 200
	body = res.json()
	assert body["context_id"]
	assert body["chunk_count"] >= 1
	assert len(body["segments"]) == 3


