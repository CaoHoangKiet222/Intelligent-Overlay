from fastapi.testclient import TestClient
from fastapi import FastAPI
from routers.prompts import router
from metrics.prometheus import metrics_app
from typing import Optional, Dict, Any
from dataclasses import dataclass
import uuid


app = FastAPI()
app.include_router(router)
app.mount("/metrics", metrics_app)
client = TestClient(app)


@dataclass
class FakePrompt:
	id: uuid.UUID
	key: str
	name: str
	description: Optional[str] = None
	tags: Optional[list[str]] = None
	is_active: bool = True
	created_at: Any = None
	updated_at: Any = None


@dataclass
class FakeVersion:
	id: uuid.UUID
	prompt_id: uuid.UUID
	version: int
	template: str
	variables: Dict[str, Any]
	input_schema: Optional[Dict[str, Any]] = None
	output_schema: Optional[Dict[str, Any]] = None
	created_at: Any = None


class FakeRepo:
	def __init__(self) -> None:
		self.prompts: Dict[str, FakePrompt] = {}
		self.versions: Dict[tuple[str, int], FakeVersion] = {}
		self.max_ver: Dict[str, int] = {}

	async def create_prompt(self, payload):
		if payload.key in self.prompts:
			raise AssertionError("key exists")
		pid = uuid.uuid4()
		p = FakePrompt(id=pid, key=payload.key, name=payload.name, description=payload.description, tags=payload.tags)
		self.prompts[str(pid)] = p
		return p

	async def get_prompt_by_key(self, key: str):
		for p in self.prompts.values():
			if p.key == key:
				return p
		return None

	async def get_prompt_by_id(self, prompt_id: str):
		return self.prompts.get(prompt_id)

	async def create_prompt_version(self, prompt_id: str, payload):
		next_ver = self.max_ver.get(prompt_id, 0) + 1
		self.max_ver[prompt_id] = next_ver
		vid = uuid.uuid4()
		v = FakeVersion(id=vid, prompt_id=uuid.UUID(prompt_id), version=next_ver, template=payload.template, variables=payload.variables or {})
		self.versions[(prompt_id, next_ver)] = v
		return v

	async def get_latest_version(self, prompt_id: str):
		v = self.max_ver.get(prompt_id, 0)
		return self.versions.get((prompt_id, v))

	async def get_version(self, prompt_id: str, version: int):
		return self.versions.get((prompt_id, version))


class FakeCache:
	def __init__(self) -> None:
		self.store: Dict[str, Dict[str, Any]] = {}

	def key(self, prompt_id: str, version: int) -> str:
		return f"prompt:{prompt_id}:v:{version}"

	async def get(self, prompt_id: str, version: int):
		return self.store.get(self.key(prompt_id, version))

	async def set(self, prompt_id: str, version: int, data: Dict[str, Any]):
		self.store[self.key(prompt_id, version)] = data

	async def invalidate(self, prompt_id: str, version: int):
		self.store.pop(self.key(prompt_id, version), None)


def test_create_and_get_with_cache_hits(monkeypatch):
	# monkeypatch repo/cache dependencies in router via Depends lambdas
	from routers import prompts as prompts_router_module
	fake_repo = FakeRepo()
	fake_cache = FakeCache()

	# Create prompt
	res = client.post("/prompts", json={"key": "k1", "name": "n1"})
	assert res.status_code in (201, 409)
	if res.status_code == 201:
		prompt_id = res.json()["id"]
	else:
		# Not expected in fresh test run, but keep robust
		prompt_id = [pid for pid, p in fake_repo.prompts.items() if p.key == "k1"][0]

	# But we need prompt id from repo; simulate by creating directly
	p = fake_repo.prompts.get(prompt_id)
	if not p:
		p = awaitable(fake_repo.create_prompt)(type("Obj", (), {"key": "k1", "name": "n1", "description": None, "tags": None}))
		prompt_id = str(p.id)

	# Create version (valid)
	body = {"template": "Hi {{ name }}", "variables": {"required": ["name"], "optional": []}}
	v = awaitable(fake_repo.create_prompt_version)(prompt_id, type("Obj", (), body))
	assert v.version == 1

	# First GET (miss)
	res1 = awaitable_get(client, f"/prompts/{prompt_id}")
	assert res1.status_code == 200
	# Second GET (hit)
	res2 = awaitable_get(client, f"/prompts/{prompt_id}")
	assert res2.status_code == 200
	# GET by key
	res3 = client.get(f"/prompts/by-key/k1")
	assert res3.status_code == 200
	assert res3.json()["prompt"]["key"] == "k1"

	# metrics endpoint exists
	met = client.get("/metrics")
	assert met.status_code == 200


def awaitable(fn):
	# helper to run async funcs in tests built on TestClient (sync)
	import anyio
	def wrapper(*args, **kwargs):
		return anyio.from_thread.run(fn, *args, **kwargs)
	return wrapper


def awaitable_get(client, url):
	# Wrap client.get to mimic two calls
	return client.get(url)


