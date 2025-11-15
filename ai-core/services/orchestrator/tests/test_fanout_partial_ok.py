import pytest
from fastapi.testclient import TestClient
from app.main import app
from domain.schemas import AnalysisTask


client = TestClient(app)


@pytest.mark.asyncio
async def test_partial_ok(monkeypatch):
	from orchestration import orchestrator_service as svc
	async def fake_handle(raw: bytes):
		return None
	monkeypatch.setattr(svc.OrchestratorService, "handle_message", fake_handle, raising=False)
	# Just ensure app mounts and health is OK
	r = client.get("/healthz")
	assert r.status_code == 200


