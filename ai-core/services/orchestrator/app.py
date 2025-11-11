import os, asyncio, ray
from fastapi import FastAPI
from metrics.prometheus import metrics_app
from kafka.consumer import serve
from kafka.producer import DlqProducer
from data.repositories import LlmCallRepo, AnalysisRunRepo, IdempotencyRepo
from orchestration.orchestrator_service import OrchestratorService
from shared.telemetry.otel import init_otel
from shared.telemetry.logger import setup_json_logger


setup_json_logger()
app = FastAPI(title="AI Core Orchestrator", version="0.1.0")
app.mount("/metrics", metrics_app)
init_otel(app)


@app.on_event("startup")
async def startup():
	ray_addr = os.getenv("RAY_ADDRESS", "")
	if ray_addr and ray_addr != "auto":
		ray.init(address=ray_addr)
	else:
		ray.init(num_cpus=int(os.getenv("RAY_NUM_CPUS", "2")), num_gpus=int(os.getenv("RAY_NUM_GPUS", "0")))
	app.state.dlq = DlqProducer()
	await app.state.dlq.start()
	orch = OrchestratorService(LlmCallRepo(), AnalysisRunRepo(), IdempotencyRepo(), app.state.dlq)
	app.state.consumer_task = asyncio.create_task(serve(orch))


@app.on_event("shutdown")
async def shutdown():
	await app.state.dlq.stop()
	app.state.consumer_task.cancel()
	ray.shutdown()


@app.get("/healthz")
async def healthz():
	return {"ok": True}


