from typing import Dict
import os
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn


class HealthResponse(BaseModel):
    status: str
    service: str


def create_app() -> FastAPI:
    application = FastAPI(title="prompt-service")

    @application.get("/healthz", response_model=HealthResponse)
    def healthz() -> HealthResponse:
        return HealthResponse(status="ok", service="prompt-service")

    @application.get("/info")
    def info() -> Dict[str, str]:
        return {"service": "prompt-service"}

    return application


app = create_app()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)


