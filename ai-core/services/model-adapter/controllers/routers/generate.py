import os
import sys
from pathlib import Path

ai_core_path = Path(__file__).parent.parent.parent.parent.parent
if str(ai_core_path) not in sys.path:
	sys.path.insert(0, str(ai_core_path))

import logging
import httpx
from fastapi import APIRouter, HTTPException
from typing import Dict

from app.config import AppConfig
from providers.registry import ProviderRegistry
from routing.policy import RouterPolicy, RoutingCriteria
from services.generation_service import GenerationService
from services.prompt_renderer import PromptRenderer
from guardrails.pipeline import apply_guardrails
from controllers.schemas import (
	ModelGenerateRequest,
	ModelGenerateResponse,
	LegacyGenerateRequest,
)
from controllers.utils import build_generate_response


def create_generate_router(
	cfg: AppConfig,
	registry: ProviderRegistry,
	policy: RouterPolicy,
	gen_service: GenerationService,
	renderer: PromptRenderer,
) -> APIRouter:
	router = APIRouter(tags=["generate"])
	logger = logging.getLogger("model-adapter")

	@router.post("/model/generate", response_model=ModelGenerateResponse)
	async def model_generate(req: ModelGenerateRequest) -> ModelGenerateResponse:
		try:
			rendered_prompt, _ = await renderer.render(req.prompt_ref, req.variables)
		except httpx.HTTPStatusError as exc:
			response_text = exc.response.text if exc.response else "No response text"
			logger.error(
				"Failed to fetch prompt from prompt-service",
				extra={
					"error_type": type(exc).__name__,
					"status_code": exc.response.status_code if exc.response else None,
					"prompt_ref": req.prompt_ref,
					"response_text": response_text[:500],
					"prompt_service_base_url": cfg.prompt_service_base_url,
				},
				exc_info=True,
			)
			raise HTTPException(
				status_code=503,
				detail=f"Failed to fetch prompt '{req.prompt_ref}' from prompt-service: {response_text[:200]}",
			)
		except httpx.RequestError as exc:
			logger.error(
				"Connection error when fetching prompt from prompt-service",
				extra={
					"error_type": type(exc).__name__,
					"error_message": str(exc),
					"prompt_ref": req.prompt_ref,
					"prompt_service_base_url": cfg.prompt_service_base_url,
				},
				exc_info=True,
			)
			raise HTTPException(
				status_code=503,
				detail=f"Cannot connect to prompt-service at {cfg.prompt_service_base_url}. Please check if prompt-service is running.",
			)
		except Exception as exc:
			logger.error(
				"Unexpected error when fetching prompt",
				extra={
					"error_type": type(exc).__name__,
					"error_message": str(exc),
					"prompt_ref": req.prompt_ref,
				},
				exc_info=True,
			)
			raise HTTPException(status_code=500, detail=f"Internal error: {str(exc)}")

		context_text = str(req.variables.get("context") or "")
		safe_payload = apply_guardrails({"prompt": rendered_prompt, "context": context_text})
		criteria = RoutingCriteria(
			cost_target=None,
			latency_target_ms=None,
			context_len=req.context_len,
			language=req.language,
			provider_hint=req.provider_hint,
		)
		provider = policy.choose_provider_for_task(req.task, criteria)
		if provider is None:
			logger.warning(
				"No suitable provider found",
				extra={
					"task": req.task,
					"language": req.language,
					"provider_hint": req.provider_hint,
					"context_len": req.context_len,
				},
			)
			raise HTTPException(status_code=422, detail="No suitable provider found")
		result = gen_service.generate(provider.name, safe_payload["prompt"])
		resp = build_generate_response(provider.name, provider.cost_per_1k_tokens, result)
		logger.info(
			"model_generate",
			extra={
				"provider": resp.provider,
				"model": resp.model,
				"tokens_in": resp.tokens_in,
				"tokens_out": resp.tokens_out,
				"latency_ms": resp.latency_ms,
				"task": req.task,
			},
		)
		return resp

	@router.post("/generate", response_model=ModelGenerateResponse, deprecated=True)
	async def legacy_generate(req: LegacyGenerateRequest) -> ModelGenerateResponse:
		safe_payload = apply_guardrails({"prompt": req.prompt, "context": None})
		criteria = RoutingCriteria(
			cost_target=None,
			latency_target_ms=None,
			context_len=req.context_len,
			language=req.language,
			provider_hint=req.provider_hint,
		)
		provider = policy.choose_provider_for_generation(criteria)
		if provider is None:
			raise HTTPException(status_code=422, detail="No suitable provider found")
		result = gen_service.generate(provider.name, safe_payload["prompt"])
		return build_generate_response(provider.name, provider.cost_per_1k_tokens, result)

	return router

