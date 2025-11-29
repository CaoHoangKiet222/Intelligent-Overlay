from __future__ import annotations

import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager
from uuid import uuid4
from time import perf_counter
import logging
import httpx
from fastapi import FastAPI, HTTPException

ai_core_path = Path(__file__).parent.parent.parent.parent
if str(ai_core_path) not in sys.path:
	sys.path.insert(0, str(ai_core_path))

from shared.telemetry.logger import setup_json_logger
from shared.telemetry.otel import init_otel
from shared.config.base import get_base_config
from app.config import DemoConfig
from domain.schemas import DemoAnalyzeRequest, DemoAnalyzeResponse, DemoAnalyzeResultResponse, DemoQARequest, DemoQAResponse
from clients.retrieval import RetrievalClient
from clients.model_adapter import ModelAdapterClient
from clients.prompt_service import PromptServiceClient
from clients.agent_service import AgentServiceClient
from services.context import ContextPipeline
from services.qa import QAService
from services.prompt_bootstrap import PromptBootstrapper, PromptProvider, DEFAULT_PROMPTS
from metrics.prometheus import metrics_app, analyze_latency, qa_latency
from kafka.producer import AnalysisTaskProducer


cfg = DemoConfig()
setup_json_logger()
logger = logging.getLogger("demo-api")

timeout_config = get_base_config().timeout_config
retrieval_client = RetrievalClient(cfg.retrieval_service_base_url, timeout=timeout_config.services.retrieval_service)
prompt_client = PromptServiceClient(cfg.prompt_service_base_url, timeout=timeout_config.services.prompt_service)
prompt_provider = PromptProvider(prompt_client, cache_ttl_sec=cfg.prompt_cache_ttl_sec)
agent_client = AgentServiceClient(cfg.agent_service_base_url, timeout=timeout_config.services.agent_service) if cfg.use_agent_service else None
qa_service = QAService(
	retrieval_client,
	prompt_provider,
	ModelAdapterClient(cfg.model_adapter_base_url, timeout=timeout_config.services.model_adapter),
	cfg.qa_prompt_key,
	cfg.provider_hint,
	top_k=cfg.qa_top_k,
	agent_client=agent_client,
	use_agent_service=cfg.use_agent_service,
)
context_pipeline = ContextPipeline(retrieval_client, cfg.context_segment_limit)
bootstrapper = PromptBootstrapper(prompt_client)


@asynccontextmanager
async def lifespan(app: FastAPI):
	logger.info("Ensuring default prompts exist")
	await bootstrapper.ensure_prompts(DEFAULT_PROMPTS)
	app.state.analysis_task_producer = AnalysisTaskProducer(
		bootstrap_servers=cfg.kafka_bootstrap,
		topic_tasks=cfg.topic_tasks,
	)
	await app.state.analysis_task_producer.start()
	yield
	await app.state.analysis_task_producer.stop()


app = FastAPI(title="AI-Core Demo API", version="0.1.0", lifespan=lifespan)
init_otel(app)
app.mount("/metrics", metrics_app)


@app.post("/demo/analyze", response_model=DemoAnalyzeResponse)
async def demo_analyze(payload: DemoAnalyzeRequest):
	t0 = perf_counter()
	context_id: str | None = None
	event_id: str | None = None
	try:
		context_bundle = await context_pipeline.create_bundle(payload.raw_text, payload.url, payload.locale)
		context_id = context_bundle.context_id
		event_id = str(uuid4())
		prompt_ids = cfg.worker_prompt_keys()
		task_payload = {
			"event_id": event_id,
			"bundle_id": None,
			"query": None,
			"segments": [segment.model_dump(by_alias=True) for segment in context_bundle.segments],
			"language": (payload.locale or "auto"),
			"prompt_ids": {
				"summary": prompt_ids["summary"],
				"argument": prompt_ids["argument"],
				"sentiment": prompt_ids["sentiment"],
				"logic_bias": prompt_ids["logic_bias"],
			},
			"meta": {
				"source": "demo-api",
				"source_url": payload.url,
				"callback_url": f"{cfg.orchestrator_base_url.rstrip('/')}/demo/analyze/callback",
			},
		}
		await app.state.analysis_task_producer.publish(task_payload)
	except httpx.HTTPStatusError as exc:
		response_text = exc.response.text if exc.response else "No response text"
		logger.error(
			"Upstream HTTP error during analyze",
			extra={
				"error_type": type(exc).__name__,
				"status_code": exc.response.status_code if exc.response else None,
				"request_url": str(exc.request.url) if exc.request else None,
				"response_text": response_text[:500],
				"context_id": context_id,
				"event_id": event_id,
			},
			exc_info=True,
		)
		raise HTTPException(status_code=exc.response.status_code, detail=response_text)
	except httpx.RequestError as exc:
		logger.error(
			"Request error during analyze",
			extra={
				"error_type": type(exc).__name__,
				"error_message": str(exc),
				"request_url": str(exc.request.url) if hasattr(exc, "request") and exc.request else None,
				"context_id": context_id,
				"event_id": event_id,
			},
			exc_info=True,
		)
		raise HTTPException(status_code=500, detail=f"Request failed: {str(exc)}")
	except Exception as exc:
		logger.error(
			"Unexpected error during analyze",
			extra={
				"error_type": type(exc).__name__,
				"error_message": str(exc),
				"context_id": context_id,
				"event_id": event_id,
			},
			exc_info=True,
		)
		raise HTTPException(status_code=500, detail=str(exc))
	finally:
		elapsed = int((perf_counter() - t0) * 1000)
		analyze_latency.observe(elapsed)
		logger.info("demo_analyze enqueued", extra={"context_id": context_id, "event_id": event_id, "took_ms": elapsed})
	if not context_id or not event_id:
		raise HTTPException(status_code=500, detail="analyze_enqueue_failed")
	return DemoAnalyzeResponse(event_id=event_id, context_id=context_id)


@app.post("/demo/analyze_direct")
async def demo_analyze_direct(payload: DemoAnalyzeRequest) -> dict[str, object]:
	t0 = perf_counter()
	context_id: str | None = None
	orchestrator_url: str | None = None
	try:
		context_bundle = await context_pipeline.create_bundle(payload.raw_text, payload.url, payload.locale)
		context_id = context_bundle.context_id
		prompt_ids = cfg.worker_prompt_keys()
		orchestrator_payload: dict[str, object] = {
			"context_id": context_bundle.context_id,
			"language": payload.locale or "auto",
			"segments": [segment.model_dump(by_alias=True) for segment in context_bundle.segments],
			"prompt_ids": {
				"summary": prompt_ids["summary"],
				"argument": prompt_ids["argument"],
				"sentiment": prompt_ids["sentiment"],
				"logic_bias": prompt_ids["logic_bias"],
			},
		}
		orchestrator_url = f"{cfg.orchestrator_base_url.rstrip('/')}/orchestrator/analyze"
		logger.debug("Calling orchestrator", extra={"url": orchestrator_url, "context_id": context_id})
		timeout = timeout_config.services.orchestrator
		async with httpx.AsyncClient(timeout=timeout) as client:
			resp = await client.post(orchestrator_url, json=orchestrator_payload)
		resp.raise_for_status()
		body = resp.json()
		return body
	except httpx.HTTPStatusError as exc:
		response_text = exc.response.text if exc.response else "No response text"
		response_body = response_text[:1000]
		logger.error(
			"Upstream HTTP error during direct analyze",
			extra={
				"error_type": type(exc).__name__,
				"status_code": exc.response.status_code if exc.response else None,
				"request_url": orchestrator_url,
				"request_method": "POST",
				"response_text": response_body,
				"context_id": context_id,
				"orchestrator_base_url": cfg.orchestrator_base_url,
			},
			exc_info=True,
		)
		raise HTTPException(status_code=exc.response.status_code, detail=response_text)
	except httpx.RequestError as exc:
		logger.error(
			"Request error during direct analyze",
			extra={
				"error_type": type(exc).__name__,
				"error_message": str(exc),
				"request_url": orchestrator_url,
				"orchestrator_base_url": cfg.orchestrator_base_url,
				"context_id": context_id,
			},
			exc_info=True,
		)
		raise HTTPException(status_code=500, detail=f"Request to orchestrator failed: {str(exc)}")
	except Exception as exc:
		logger.error(
			"Unexpected error during direct analyze",
			extra={
				"error_type": type(exc).__name__,
				"error_message": str(exc),
				"request_url": orchestrator_url,
				"context_id": context_id,
			},
			exc_info=True,
		)
		raise HTTPException(status_code=500, detail=str(exc))
	finally:
		elapsed = int((perf_counter() - t0) * 1000)
		analyze_latency.observe(elapsed)
		logger.info("demo_analyze_direct completed", extra={"context_id": context_id, "took_ms": elapsed})


@app.get("/demo/analyze/{event_id}", response_model=DemoAnalyzeResultResponse)
async def demo_analyze_result(event_id: str):
	t0 = perf_counter()
	try:
		url = f"{cfg.orchestrator_base_url.rstrip('/')}/orchestrator/runs/{event_id}"
		timeout = timeout_config.http_default.to_httpx_simple_timeout()
		async with httpx.AsyncClient(timeout=timeout) as client:
			resp = await client.get(url)
		if resp.status_code == 404:
			raise HTTPException(status_code=404, detail="analysis_not_found")
		resp.raise_for_status()
		body = resp.json()
		return DemoAnalyzeResultResponse(**body)
	except httpx.HTTPStatusError as exc:
		response_text = exc.response.text if exc.response else "No response text"
		logger.error(
			"Upstream HTTP error during analyze result fetch",
			extra={
				"error_type": type(exc).__name__,
				"status_code": exc.response.status_code if exc.response else None,
				"request_url": str(exc.request.url) if exc.request else None,
				"response_text": response_text[:500],
				"event_id": event_id,
			},
			exc_info=True,
		)
		raise HTTPException(status_code=exc.response.status_code, detail=response_text)
	except httpx.RequestError as exc:
		logger.error(
			"Request error during analyze result fetch",
			extra={
				"error_type": type(exc).__name__,
				"error_message": str(exc),
				"request_url": str(exc.request.url) if hasattr(exc, "request") and exc.request else None,
				"event_id": event_id,
			},
			exc_info=True,
		)
		raise HTTPException(status_code=500, detail=f"Request failed: {str(exc)}")
	except Exception as exc:
		logger.error(
			"Unexpected error during analyze result fetch",
			extra={
				"error_type": type(exc).__name__,
				"error_message": str(exc),
				"event_id": event_id,
			},
			exc_info=True,
		)
		raise HTTPException(status_code=500, detail=str(exc))
	finally:
		elapsed = int((perf_counter() - t0) * 1000)
		logger.info("demo_analyze_result completed", extra={"event_id": event_id, "took_ms": elapsed})


@app.post("/demo/analyze/callback")
async def demo_analyze_callback(payload: DemoAnalyzeResultResponse):
	try:
		logger.info(
			"demo_analyze_callback received",
			extra={
				"event_id": payload.event_id,
				"status": payload.status,
				"has_summary": payload.summary_json is not None,
				"has_argument": payload.argument_json is not None,
				"has_sentiment": payload.sentiment_json is not None,
				"has_logic_bias": payload.logic_bias_json is not None,
				"error_summary": payload.error_summary,
			},
		)
		return {"ok": True}
	except Exception as exc:
		logger.error(
			"Error processing analyze callback",
			extra={
				"error_type": type(exc).__name__,
				"error_message": str(exc),
				"payload_event_id": getattr(payload, "event_id", None),
			},
			exc_info=True,
		)
		raise HTTPException(status_code=500, detail=str(exc))


@app.post("/demo/qa", response_model=DemoQAResponse)
async def demo_qa(payload: DemoQARequest):
	t0 = perf_counter()
	try:
		result = await qa_service.answer(payload.context_id, payload.query, locale="auto")
	except httpx.HTTPStatusError as exc:
		response_text = exc.response.text if exc.response else "No response text"
		logger.error(
			"Upstream HTTP error during qa",
			extra={
				"error_type": type(exc).__name__,
				"status_code": exc.response.status_code if exc.response else None,
				"request_url": str(exc.request.url) if exc.request else None,
				"response_text": response_text[:500],
				"context_id": payload.context_id,
				"query": payload.query[:200],
			},
			exc_info=True,
		)
		raise HTTPException(status_code=exc.response.status_code, detail=response_text)
	except httpx.RequestError as exc:
		logger.error(
			"Request error during qa",
			extra={
				"error_type": type(exc).__name__,
				"error_message": str(exc),
				"request_url": str(exc.request.url) if hasattr(exc, "request") and exc.request else None,
				"context_id": payload.context_id,
				"query": payload.query[:200],
			},
			exc_info=True,
		)
		raise HTTPException(status_code=500, detail=f"Request failed: {str(exc)}")
	except Exception as exc:
		logger.error(
			"Unexpected error during qa",
			extra={
				"error_type": type(exc).__name__,
				"error_message": str(exc),
				"context_id": payload.context_id,
				"query": payload.query[:200],
			},
			exc_info=True,
		)
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

