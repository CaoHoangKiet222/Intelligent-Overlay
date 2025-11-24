import os
import sys
from pathlib import Path

ai_core_path = Path(__file__).parent.parent.parent.parent
if str(ai_core_path) not in sys.path:
	sys.path.insert(0, str(ai_core_path))

import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
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
from clients.prompt_service import PromptServiceClient
from domain.models import GenerationResult


class HealthResponse(BaseModel):
	status: str
	service: str


class ModelGenerateRequest(BaseModel):
	prompt_ref: str
	variables: Dict[str, Any] = Field(default_factory=dict)
	task: Literal["summary", "qa", "argument", "logic_bias", "default"] = "default"
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


class EmbedResponse(BaseModel):
	provider: str
	model: str
	vectors: List[List[float]]


def create_app() -> FastAPI:
	cfg = AppConfig.from_env()
	registry = ProviderRegistry.from_config(cfg)
	policy = RouterPolicy(registry, cfg.task_routing)
	gen_service = GenerationService(registry, policy)
	prompt_client = PromptServiceClient(cfg.prompt_service_base_url)
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
		rendered_prompt, _ = await renderer.render(req.prompt_ref, req.variables)
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
		return EmbedResponse(provider=provider.name, model=result.model, vectors=result.vectors)

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
