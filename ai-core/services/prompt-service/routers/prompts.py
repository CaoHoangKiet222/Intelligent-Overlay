import uuid
from urllib.parse import unquote
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional, Dict, Any
from domain.schemas import PromptCreate, PromptVersionCreate
from domain.validators import validate_template
from data.repositories import PromptRepo
from cache.redis_cache import PromptCache
from app.deps import get_cache_dep, get_repo_dep
from metrics.prometheus import prompt_cache_hit, prompt_cache_miss, prompt_cache_invalidate


router = APIRouter(prefix="/prompts", tags=["prompts"])


def _build_payload(pr, pv) -> Dict[str, Any]:
	return {
		"prompt": {
			"id": str(pr.id),
			"key": pr.key,
			"name": pr.name,
			"description": pr.description,
			"tags": pr.tags,
			"is_active": pr.is_active,
			"created_at": pr.created_at.isoformat() if pr.created_at else None,
			"updated_at": pr.updated_at.isoformat() if pr.updated_at else None,
		},
		"version": {
			"id": str(pv.id),
			"prompt_id": str(pr.id),
			"version": pv.version,
			"template": pv.template,
			"variables": pv.variables or {},
			"input_schema": pv.input_schema,
			"output_schema": pv.output_schema,
			"created_at": pv.created_at.isoformat() if pv.created_at else None,
		},
	}


@router.post("", status_code=201)
async def create_prompt(payload: PromptCreate, repo: PromptRepo = Depends(get_repo_dep)) -> Dict[str, Any]:
	if await repo.get_prompt_by_key(payload.key):
		raise HTTPException(status_code=409, detail="prompt key already exists")
	pr = await repo.create_prompt(payload)
	return {"id": str(pr.id)}


@router.post("/{prompt_id}/versions", status_code=201)
async def create_version(prompt_id: str, payload: PromptVersionCreate,
                         repo: PromptRepo = Depends(get_repo_dep),
                         cache: PromptCache = Depends(get_cache_dep)) -> Dict[str, Any]:
	validate_template(payload.template, payload.variables or {})
	pv = await repo.create_prompt_version(prompt_id, payload)
	await cache.invalidate(prompt_id, pv.version)
	prompt_cache_invalidate.inc()
	return {"id": str(pv.id), "version": pv.version}


def _is_uuid(s: str) -> bool:
	try:
		uuid.UUID(s)
		return True
	except (ValueError, AttributeError):
		return False


@router.get("/{prompt_id}")
async def get_prompt(prompt_id: str, version: Optional[int] = Query(default=None),
                     repo: PromptRepo = Depends(get_repo_dep),
                     cache: PromptCache = Depends(get_cache_dep)) -> Dict[str, Any]:
	prompt_id = unquote(prompt_id)
	prompt_key: str | None = None
	actual_prompt_id: str | None = None

	if prompt_id.startswith("key:"):
		prompt_key = prompt_id[4:]
		pr = await repo.get_prompt_by_key(prompt_key)
		if not pr:
			raise HTTPException(status_code=404, detail=f"prompt not found for key: {prompt_key}")
		actual_prompt_id = str(pr.id)
	elif _is_uuid(prompt_id):
		actual_prompt_id = prompt_id
		pr = await repo.get_prompt_by_id(actual_prompt_id)
		if not pr:
			raise HTTPException(status_code=404, detail="prompt not found")
	else:
		prompt_key = prompt_id
		pr = await repo.get_prompt_by_key(prompt_key)
		if not pr:
			raise HTTPException(status_code=404, detail=f"prompt not found for key: {prompt_key}")
		actual_prompt_id = str(pr.id)

	if version is None:
		pv = await repo.get_latest_version(actual_prompt_id)
		if not pv:
			raise HTTPException(status_code=404, detail="prompt version not found")
		version = pv.version

	cached = await cache.get(actual_prompt_id, version)
	if cached:
		prompt_cache_hit.inc()
		return cached

	pv = await repo.get_version(actual_prompt_id, version)
	if not pv:
		raise HTTPException(status_code=404, detail="prompt version not found")

	result = _build_payload(pr, pv)
	await cache.set(actual_prompt_id, version, result)
	prompt_cache_miss.inc()
	return result


@router.get("/by-key/{prompt_key}")
async def get_prompt_by_key(prompt_key: str, version: Optional[int] = Query(default=None),
                            repo: PromptRepo = Depends(get_repo_dep),
                            cache: PromptCache = Depends(get_cache_dep)) -> Dict[str, Any]:
	pr = await repo.get_prompt_by_key(prompt_key)
	if not pr:
		raise HTTPException(status_code=404, detail="prompt not found")

	prompt_id = str(pr.id)
	target_version = version
	if target_version is None:
		pv = await repo.get_latest_version(prompt_id)
		if not pv:
			raise HTTPException(status_code=404, detail="prompt version not found")
		target_version = pv.version
	else:
		pv = await repo.get_version(prompt_id, target_version)
		if not pv:
			raise HTTPException(status_code=404, detail="prompt version not found")

	cached = await cache.get(prompt_id, target_version)
	if cached:
		prompt_cache_hit.inc()
		return cached

	result = _build_payload(pr, pv)
	await cache.set(prompt_id, target_version, result)
	prompt_cache_miss.inc()
	return result


