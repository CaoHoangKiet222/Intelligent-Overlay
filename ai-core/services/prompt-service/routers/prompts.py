from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional, Dict, Any
from domain.schemas import PromptCreate, PromptVersionCreate
from domain.validators import validate_template
from data.repositories import PromptRepo
from cache.redis_cache import PromptCache
from metrics.prometheus import prompt_cache_hit, prompt_cache_miss, prompt_cache_invalidate


router = APIRouter(prefix="/prompts", tags=["prompts"])


@router.post("", status_code=201)
async def create_prompt(payload: PromptCreate, repo: PromptRepo = Depends(lambda: PromptRepo())) -> Dict[str, Any]:
	if await repo.get_prompt_by_key(payload.key):
		raise HTTPException(status_code=409, detail="prompt key already exists")
	pr = await repo.create_prompt(payload)
	return {"id": str(pr.id)}


@router.post("/{prompt_id}/versions", status_code=201)
async def create_version(prompt_id: str, payload: PromptVersionCreate,
                         repo: PromptRepo = Depends(lambda: PromptRepo()),
                         cache: PromptCache = Depends(lambda: PromptCache("redis://redis:6379/0"))) -> Dict[str, Any]:
	validate_template(payload.template, payload.variables or {})
	pv = await repo.create_prompt_version(prompt_id, payload)
	await cache.invalidate(prompt_id, pv.version)
	prompt_cache_invalidate.inc()
	return {"id": str(pv.id), "version": pv.version}


@router.get("/{prompt_id}")
async def get_prompt(prompt_id: str, version: Optional[int] = Query(default=None),
                     repo: PromptRepo = Depends(lambda: PromptRepo()),
                     cache: PromptCache = Depends(lambda: PromptCache("redis://redis:6379/0"))) -> Dict[str, Any]:
	if version is None:
		pv = await repo.get_latest_version(prompt_id)
		if not pv:
			raise HTTPException(status_code=404, detail="prompt version not found")
		version = pv.version

	cached = await cache.get(prompt_id, version)
	if cached:
		prompt_cache_hit.inc()
		return cached

	pr = await repo.get_prompt_by_id(prompt_id)
	if not pr:
		raise HTTPException(status_code=404, detail="prompt not found")

	pv = await repo.get_version(prompt_id, version)
	if not pv:
		raise HTTPException(status_code=404, detail="prompt version not found")

	result: Dict[str, Any] = {
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
	await cache.set(prompt_id, version, result)
	prompt_cache_miss.inc()
	return result


