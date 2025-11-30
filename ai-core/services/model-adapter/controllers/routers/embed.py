import os
import sys
from pathlib import Path

ai_core_path = Path(__file__).parent.parent.parent.parent.parent
if str(ai_core_path) not in sys.path:
	sys.path.insert(0, str(ai_core_path))

from fastapi import APIRouter
from providers.registry import ProviderRegistry
from routing.policy import RouterPolicy
from services.generation_service import GenerationService
from controllers.schemas import EmbedRequest, EmbedResponse


def create_embed_router(
	policy: RouterPolicy,
	gen_service: GenerationService,
) -> APIRouter:
	router = APIRouter(tags=["embed"])

	@router.post("/model/embed", response_model=EmbedResponse)
	def model_embed(req: EmbedRequest) -> EmbedResponse:
		provider = policy.choose_provider_for_embedding(req.model_hint)
		result = gen_service.embed(provider.name, req.texts)
		dim = result.dim if result.dim is not None else (len(result.vectors[0]) if result.vectors else 0)
		return EmbedResponse(provider=provider.name, model=result.model, dim=dim, vectors=result.vectors)

	@router.post("/embed", response_model=EmbedResponse, deprecated=True)
	def legacy_embed(req: EmbedRequest) -> EmbedResponse:
		return model_embed(req)

	return router

