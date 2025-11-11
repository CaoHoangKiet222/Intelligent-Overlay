import pytest
from fastapi.testclient import TestClient
from app import app


client = TestClient(app)


def test_healthz():
	r = client.get("/healthz")
	assert r.status_code == 200


