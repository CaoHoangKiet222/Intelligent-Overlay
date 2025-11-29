import os
import sys
from pathlib import Path

ai_core_path = Path(__file__).parent.parent.parent.parent
if str(ai_core_path) not in sys.path:
	sys.path.insert(0, str(ai_core_path))

import logging
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Optional, Any, Literal

from app.config import AppConfig
from providers.registry import ProviderRegistry
from routing.policy import RouterPolicy, RoutingCriteria
from services.generation_service import GenerationService
from services.prompt_renderer import PromptRenderer
from guardrails.pipeline import apply_guardrails
from shared.telemetry.otel import init_otel
from shared.telemetry.logger import setup_json_logger
from shared.telemetry.metrics import metrics_app
from shared.config.base import get_base_config
from clients.prompt_service import PromptServiceClient
from domain.models import GenerationResult


class HealthResponse(BaseModel):
	status: str
	service: str


class ModelGenerateRequest(BaseModel):
	prompt_ref: str
	variables: Dict[str, Any] = Field(default_factory=dict)
	task: Literal["summary", "qa", "argument", "logic_bias", "sentiment", "default"] = "default"
	language: Optional[str] = None
	context_len: Optional[int] = None
	provider_hint: Optional[str] = None


class ModelGenerateResponse(BaseModel):
	provider: str
	model: str
	output: str
	tokens_in: Optional[int] = None
	tokens_out: Optional[int] = None
	latency_ms: Optional[int] = None
	cost_usd: Optional[float] = None


class LegacyGenerateRequest(BaseModel):
	prompt: str
	language: Optional[str] = None
	context_len: Optional[int] = None
	provider_hint: Optional[str] = None


class EmbedRequest(BaseModel):
	texts: List[str]
	model_hint: Optional[str] = None
	model_config = ConfigDict(protected_namespaces=())


class EmbedResponse(BaseModel):
	provider: str
	model: str
	dim: int
	vectors: List[List[float]]


def create_app() -> FastAPI:
	cfg = AppConfig.from_env()
	registry = ProviderRegistry.from_config(cfg)
	policy = RouterPolicy(registry, cfg.task_routing)
	gen_service = GenerationService(registry, policy)
	timeout_config = get_base_config().timeout_config
	prompt_client = PromptServiceClient(
		cfg.prompt_service_base_url,
		timeout=timeout_config.services.prompt_service
	)
	renderer = PromptRenderer(prompt_client)
	logger = logging.getLogger("model-adapter")

	setup_json_logger()
	app = FastAPI(title="model-adapter")
	app.mount("/metrics", metrics_app)
	init_otel(app)

	@app.get("/healthz", response_model=HealthResponse)
	def healthz() -> HealthResponse:
		return HealthResponse(status="ok", service="model-adapter")

	@app.get("/providers")
	def providers() -> Dict[str, Dict[str, str | int | float]]:
		return registry.list_providers_summary()

	@app.post("/model/generate", response_model=ModelGenerateResponse)
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
		resp = _build_generate_response(provider.name, provider.cost_per_1k_tokens, result)
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

	@app.post("/generate", response_model=ModelGenerateResponse, deprecated=True)
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
		return _build_generate_response(provider.name, provider.cost_per_1k_tokens, result)

	@app.post("/model/embed", response_model=EmbedResponse)
	def model_embed(req: EmbedRequest) -> EmbedResponse:
		provider = policy.choose_provider_for_embedding(req.model_hint)
		result = gen_service.embed(provider.name, req.texts)
		dim = result.dim if result.dim is not None else (len(result.vectors[0]) if result.vectors else 0)
		return EmbedResponse(provider=provider.name, model=result.model, dim=dim, vectors=result.vectors)

	@app.post("/embed", response_model=EmbedResponse, deprecated=True)
	def legacy_embed(req: EmbedRequest) -> EmbedResponse:
		return model_embed(req)

	return app


def _build_generate_response(provider_name: str, cost_per_1k: float, result: GenerationResult) -> ModelGenerateResponse:
	token_total = (result.tokens_in or 0) + (result.tokens_out or 0)
	cost_usd = round((token_total / 1000) * cost_per_1k, 6) if token_total else None
	return ModelGenerateResponse(
		provider=provider_name,
		model=result.model,
		output=result.text,
		tokens_in=result.tokens_in,
		tokens_out=result.tokens_out,
		latency_ms=result.latency_ms,
		cost_usd=cost_usd,
	)
