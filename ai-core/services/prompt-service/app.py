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


