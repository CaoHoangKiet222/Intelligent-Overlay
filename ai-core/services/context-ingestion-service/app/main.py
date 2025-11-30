from contextlib import asynccontextmanager
from fastapi import FastAPI
from routers.contexts import router as contexts_router
from metrics.prometheus import metrics_app
from data.db import ensure_extensions


@asynccontextmanager
async def lifespan(_app: FastAPI):
	await ensure_extensions()
	yield


app = FastAPI(title="Context Ingestion Service", version="0.1.0", lifespan=lifespan)
app.include_router(contexts_router)
app.mount("/metrics", metrics_app)

@app.get("/healthz")
async def healthz():
	return {"ok": True}


if __name__ == "__main__":
	import uvicorn
	import logging
	import os
	
	port = int(os.getenv("PORT", "8000"))
	debug_mode = os.getenv("DEBUG", "false").lower() == "true"
	log_level = logging.DEBUG if debug_mode else logging.INFO
	
	logging.basicConfig(
		level=log_level,
		format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
	)
	logger = logging.getLogger(__name__)
	logger.info(f"Starting Context Ingestion Service on port {port}")
	logger.info(f"Debug mode: {debug_mode}")
	logger.info(f"Health check: http://localhost:{port}/healthz")
	logger.info(f"Metrics: http://localhost:{port}/metrics")
	
	uvicorn.run(
		"app.main:app",
		host="0.0.0.0",
		port=port,
		reload=debug_mode,
		log_level="debug" if debug_mode else "info"
	)

