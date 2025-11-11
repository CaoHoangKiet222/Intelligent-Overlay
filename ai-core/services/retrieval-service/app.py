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


