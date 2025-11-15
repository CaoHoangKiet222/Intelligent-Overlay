import os
import sys
import asyncio
import ray
from pathlib import Path
from contextlib import asynccontextmanager

ai_core_path = Path(__file__).parent.parent.parent.parent
if str(ai_core_path) not in sys.path:
	sys.path.insert(0, str(ai_core_path))

from fastapi import FastAPI
from metrics.prometheus import metrics_app
from kafka.consumer import serve
from kafka.producer import DlqProducer
from data.repositories import LlmCallRepo, AnalysisRunRepo, IdempotencyRepo
from orchestration.orchestrator_service import OrchestratorService
from shared.telemetry.otel import init_otel
from shared.telemetry.logger import setup_json_logger


setup_json_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
	ray_addr = os.getenv("RAY_ADDRESS", "")
	# Check if Ray is already initialized
	if not ray.is_initialized():
		# If RAY_ADDRESS is set to a specific address (not "auto" or empty), connect to it
		if ray_addr and ray_addr != "auto" and ray_addr != "":
			ray.init(address=ray_addr)
		else:
			# Initialize local Ray instance (for "auto" or empty, start new local instance)
			ray.init(
				num_cpus=int(os.getenv("RAY_NUM_CPUS", "2")),
				num_gpus=int(os.getenv("RAY_NUM_GPUS", "0")),
				ignore_reinit_error=True
			)
	app.state.dlq = DlqProducer()
	await app.state.dlq.start()
	orch = OrchestratorService(LlmCallRepo(), AnalysisRunRepo(), IdempotencyRepo(), app.state.dlq)
	# Start Kafka consumer task (will handle connection errors gracefully)
	app.state.consumer_task = asyncio.create_task(serve(orch))
	yield
	await app.state.dlq.stop()
	app.state.consumer_task.cancel()
	ray.shutdown()


app = FastAPI(title="AI Core Orchestrator", version="0.1.0", lifespan=lifespan)
app.mount("/metrics", metrics_app)
init_otel(app)


@app.get("/healthz")
async def healthz():
	return {"ok": True}


if __name__ == "__main__":
	import uvicorn
	import logging
	
	port = int(os.getenv("PORT", "8000"))
	logging.basicConfig(level=logging.INFO)
	logger = logging.getLogger(__name__)
	logger.info(f"Starting Orchestrator Service on port {port}")
	logger.info(f"Health check: http://localhost:{port}/healthz")
	logger.info(f"Metrics: http://localhost:{port}/metrics")
	
	uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)

