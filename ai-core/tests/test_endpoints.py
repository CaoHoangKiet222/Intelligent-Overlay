from fastapi.testclient import TestClient
from services.model_adapter.controllers.api import app


client = TestClient(app)


def test_get_providers_ok():
	r = client.get("/providers")
	assert r.status_code == 200
	body = r.json()
	assert isinstance(body, dict)
	assert "openai" in body


def test_generate_routes_by_context_and_cost(monkeypatch):
	# Force provider_hint via payload to ensure routing path exercised
	payload = {
		"prompt": "hello",
		"context_len": 100000,
		"cost_target": 1.0,
		"language": "vi",
	}
	r = client.post("/generate", json=payload)
	assert r.status_code == 200
	data = r.json()
	assert data["provider"] in {"openai", "anthropic", "mistral", "ollama"}
	assert data["output"].startswith(f"[{data['provider']}]")


def test_embed_ok():
	r = client.post("/embed", json={"texts": ["a", "bb", "ccc"]})
	assert r.status_code == 200
	data = r.json()
	assert len(data["vectors"]) == 3
	assert all(isinstance(x, list) for x in data["vectors"])


