# AI Core Monorepo — Hướng dẫn chạy nhanh

## Yêu cầu môi trường

- Docker + Docker Compose (khuyến nghị)
- Python 3.11 (nếu chạy local từng service)

## Khởi động toàn bộ bằng Docker Compose

1. Sao chép file env mẫu (tùy chọn):

- `cp ai-core/env.example .env` (hoặc tự đặt biến môi trường)

2. Chạy:

- `docker compose up -d --build`

3. Kiểm tra health:

- Model Adapter: `curl http://localhost:8081/healthz`
- Prompt Service: `curl http://localhost:8082/healthz`
- Retrieval Service: `curl http://localhost:8083/healthz`
- Agent Service: `curl http://localhost:8084/healthz`
- Orchestrator: `curl http://localhost:8085/healthz`

4. Migrations (nếu cần):

- Prompt/Retrieval/Orchestrator dùng schema từ P2/P6. Chạy Alembic tại thư mục migrations tương ứng hoặc tại `ai-core/db`:
- `cd ai-core/db`
- `python3 -m venv .venv`
- `source .venv/bin/activate`
- `pip install -r requirements.txt`
- `DB_DSN="postgresql+psycopg://ai:ai@localhost:5432/ai_core" alembic upgrade head`

## Services

- Model Adapter (FastAPI): `ai-core/services/model-adapter` (POST /generate, POST /embed, GET /providers)
- Prompt Service (FastAPI): `ai-core/services/prompt-service` (CRUD prompt/version + cache)
- Retrieval Service (FastAPI): `ai-core/services/retrieval-service` (POST /ingest, POST /search)
- Agent Service (FastAPI + LangGraph): `ai-core/services/agent-service` (POST /agent/ask)
- Orchestrator (Kafka + Ray + FastAPI): `ai-core/services/orchestrator`

Mỗi service có README riêng hướng dẫn chạy local và endpoints.

## Telemetry (tùy chọn)

- /metrics (Prometheus) đã mount trong các service chính.
- OpenTelemetry: đặt `SERVICE_NAME` và `OTLP_ENDPOINT` để bật traces.
- Logger JSON cho Loki (Promtail) đã cấu hình trong code; đảm bảo `LOG_LEVEL` phù hợp.

# Intelligent-Overlay
