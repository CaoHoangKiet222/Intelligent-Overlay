import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Optional

from config import AppConfig
from providers.registry import ProviderRegistry
from routing.policy import RouterPolicy, RoutingCriteria
from services.generation_service import GenerationService
from guardrails.pipeline import apply_guardrails


class HealthResponse(BaseModel):
	status: str
	service: str


class GenerateRequest(BaseModel):
	prompt: str
	language: Optional[str] = None
	context_len: Optional[int] = None
	cost_target: Optional[float] = None
	latency_target_ms: Optional[int] = Field(default=None, ge=1)
	provider_hint: Optional[str] = None


class GenerateResponse(BaseModel):
	provider: str
	output: str


class EmbedRequest(BaseModel):
	texts: List[str]
	model_hint: Optional[str] = None


class EmbedResponse(BaseModel):
	provider: str
	vectors: List[List[float]]


def create_app() -> FastAPI:
	cfg = AppConfig.from_env()
	registry = ProviderRegistry.from_config(cfg)
	policy = RouterPolicy(registry)
	gen_service = GenerationService(registry, policy)

	app = FastAPI(title="model-adapter")

	@app.get("/healthz", response_model=HealthResponse)
	def healthz() -> HealthResponse:
		return HealthResponse(status="ok", service="model-adapter")

	@app.get("/providers")
	def providers() -> Dict[str, Dict[str, str | int | float]]:
		return registry.list_providers_summary()

	@app.post("/generate", response_model=GenerateResponse)
	def generate(req: GenerateRequest) -> GenerateResponse:
		# Guardrails: normalize + PII mask + policy check + system prompt prepend
		payload = {"prompt": req.prompt, "context": None}
		safe_payload = apply_guardrails(payload)
		redacted_prompt = safe_payload["prompt"]
		criteria = RoutingCriteria(
			cost_target=req.cost_target,
			latency_target_ms=req.latency_target_ms,
			context_len=req.context_len,
			language=req.language,
			provider_hint=req.provider_hint,
		)
		provider = policy.choose_provider_for_generation(criteria)
		if provider is None:
			raise HTTPException(status_code=422, detail="No suitable provider found")
		output = gen_service.generate(provider.name, redacted_prompt)
		return GenerateResponse(provider=provider.name, output=output)

	@app.post("/embed", response_model=EmbedResponse)
	def embed(req: EmbedRequest) -> EmbedResponse:
		provider_name = req.model_hint or policy.default_embedding_provider()
		vectors = gen_service.embed(provider_name, req.texts)
		return EmbedResponse(provider=provider_name, vectors=vectors)

	return app
