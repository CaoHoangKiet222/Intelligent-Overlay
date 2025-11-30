import os
import sys
from pathlib import Path

ai_core_path = Path(__file__).parent.parent.parent.parent.parent
if str(ai_core_path) not in sys.path:
	sys.path.insert(0, str(ai_core_path))

from fastapi import APIRouter
from typing import Dict
from providers.registry import ProviderRegistry
from controllers.schemas import HealthResponse


def create_health_router(registry: ProviderRegistry) -> APIRouter:
	router = APIRouter(tags=["health"])

	@router.get("/healthz", response_model=HealthResponse)
	def healthz() -> HealthResponse:
		return HealthResponse(status="ok", service="model-adapter")

	@router.get("/providers")
	def providers() -> Dict[str, Dict[str, str | int | float]]:
		return registry.list_providers_summary()

	return router

