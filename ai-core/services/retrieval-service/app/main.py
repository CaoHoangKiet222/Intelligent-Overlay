from fastapi import FastAPI
from routers.ingest import router as ingest_router
from routers.search import router as search_router
from metrics.prometheus import metrics_app


app = FastAPI(title="Retrieval Service", version="0.1.0")
app.include_router(ingest_router)
app.include_router(search_router)
app.mount("/metrics", metrics_app)

@app.get("/healthz")
async def healthz():
	return {"ok": True}


if __name__ == "__main__":
	import uvicorn
	import logging
	import os
	
	port = int(os.getenv("PORT", "8000"))
	logging.basicConfig(level=logging.INFO)
	logger = logging.getLogger(__name__)
	logger.info(f"Starting Retrieval Service on port {port}")
	logger.info(f"Health check: http://localhost:{port}/healthz")
	logger.info(f"Metrics: http://localhost:{port}/metrics")
	
	uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)

