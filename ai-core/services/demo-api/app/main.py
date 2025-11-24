from __future__ import annotations

import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager
from time import perf_counter
import logging
import httpx
from fastapi import FastAPI, HTTPException

ai_core_path = Path(__file__).parent.parent.parent.parent
if str(ai_core_path) not in sys.path:
	sys.path.insert(0, str(ai_core_path))

from shared.telemetry.logger import setup_json_logger
from shared.telemetry.otel import init_otel
from app.config import DemoConfig
from domain.schemas import DemoAnalyzeRequest, DemoAnalyzeResponse, DemoQARequest, DemoQAResponse
from clients.retrieval import RetrievalClient
from clients.model_adapter import ModelAdapterClient
from clients.prompt_service import PromptServiceClient
from services.context import ContextPipeline
from services.analysis import AnalysisService
from services.qa import QAService
from services.prompt_bootstrap import PromptBootstrapper, PromptProvider, DEFAULT_PROMPTS
from metrics.prometheus import metrics_app, analyze_latency, qa_latency


cfg = DemoConfig()
setup_json_logger()
logger = logging.getLogger("demo-api")

retrieval_client = RetrievalClient(cfg.retrieval_service_base_url)
prompt_client = PromptServiceClient(cfg.prompt_service_base_url)
model_client = ModelAdapterClient(cfg.model_adapter_base_url)
prompt_provider = PromptProvider(prompt_client, cache_ttl_sec=cfg.prompt_cache_ttl_sec)
analysis_service = AnalysisService(prompt_provider, model_client, cfg.worker_prompt_keys(), cfg.provider_hint)
qa_service = QAService(retrieval_client, prompt_provider, model_client, cfg.qa_prompt_key, cfg.provider_hint, top_k=cfg.qa_top_k)
context_pipeline = ContextPipeline(retrieval_client, cfg.context_segment_limit)
bootstrapper = PromptBootstrapper(prompt_client)


@asynccontextmanager
async def lifespan(app: FastAPI):
	logger.info("Ensuring default prompts exist")
	await bootstrapper.ensure_prompts(DEFAULT_PROMPTS)
	yield


app = FastAPI(title="AI-Core Demo API", version="0.1.0", lifespan=lifespan)
init_otel(app)
app.mount("/metrics", metrics_app)


@app.post("/demo/analyze", response_model=DemoAnalyzeResponse)
async def demo_analyze(payload: DemoAnalyzeRequest):
	t0 = perf_counter()
	result: DemoAnalyzeResponse | None = None
	context_id: str | None = None
	try:
		context_bundle = await context_pipeline.create_bundle(payload.raw_text, payload.url, payload.locale)
		context_id = context_bundle.context_id
		result_bundle = await analysis_service.run(context_bundle)
		result = DemoAnalyzeResponse(**result_bundle.model_dump())
	except httpx.HTTPStatusError as exc:
		logger.exception("Upstream error during analyze: %s", exc)
		raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)
	except Exception as exc:
		logger.exception("Unexpected error during analyze")
		raise HTTPException(status_code=500, detail=str(exc))
	finally:
		elapsed = int((perf_counter() - t0) * 1000)
		analyze_latency.observe(elapsed)
		logger.info("demo_analyze completed", extra={"context_id": context_id, "took_ms": elapsed})
	return result


@app.post("/demo/qa", response_model=DemoQAResponse)
async def demo_qa(payload: DemoQARequest):
	t0 = perf_counter()
	try:
		result = await qa_service.answer(payload.context_id, payload.query, locale="auto")
	except httpx.HTTPStatusError as exc:
		logger.exception("Upstream error during qa")
		raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)
	except Exception as exc:
		logger.exception("Unexpected error during qa")
		raise HTTPException(status_code=500, detail=str(exc))
	finally:
		elapsed = int((perf_counter() - t0) * 1000)
		qa_latency.observe(elapsed)
		logger.info("demo_qa completed", extra={"context_id": payload.context_id, "took_ms": elapsed})
	return result


@app.get("/healthz")
async def healthz():
	return {"ok": True}


if __name__ == "__main__":
	import uvicorn
	port = int(os.getenv("PORT", "8000"))
	logger.info("Starting Demo API on port %s", port)
	uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)

