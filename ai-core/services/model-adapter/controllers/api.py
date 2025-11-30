import os
import sys
from pathlib import Path

ai_core_path = Path(__file__).parent.parent.parent.parent
if str(ai_core_path) not in sys.path:
	sys.path.insert(0, str(ai_core_path))

from fastapi import FastAPI
from app.config import AppConfig
from providers.registry import ProviderRegistry
from routing.policy import RouterPolicy
from services.generation_service import GenerationService
from services.prompt_renderer import PromptRenderer
from shared.telemetry.otel import init_otel
from shared.telemetry.logger import setup_json_logger
from shared.telemetry.metrics import metrics_app
from shared.config.base import get_base_config
from clients.prompt_service import PromptServiceClient
from controllers.routers import health, generate, embed, transcribe, ocr


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

	setup_json_logger()
	app = FastAPI(title="model-adapter")
	app.mount("/metrics", metrics_app)
	init_otel(app)

	app.include_router(health.create_health_router(registry))
	app.include_router(generate.create_generate_router(cfg, registry, policy, gen_service, renderer))
	app.include_router(embed.create_embed_router(policy, gen_service))
	app.include_router(transcribe.create_transcribe_router(gen_service))
	app.include_router(ocr.create_ocr_router(gen_service))

	return app
