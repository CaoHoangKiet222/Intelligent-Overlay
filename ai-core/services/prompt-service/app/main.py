from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from routers.prompts import router as prompts_router
from metrics.prometheus import metrics_app


app = FastAPI(title="Prompt Service", version="0.1.0")

app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

app.include_router(prompts_router)
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
	logger.info(f"Starting Prompt Service on port {port}")
	logger.info(f"Health check: http://localhost:{port}/healthz")
	logger.info(f"Metrics: http://localhost:{port}/metrics")
	
	uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)

