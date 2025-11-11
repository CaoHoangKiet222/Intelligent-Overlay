# Prompt Service

Quản lý Prompt + Versioning + Cache Redis + Jinja2 validation.

## Chạy nhanh (Docker)

- `docker compose up -d --build prompt-service`
- Health: `curl http://localhost:8082/healthz`
- Metrics: `curl http://localhost:8082/metrics`

## Chạy local

- `cd ai-core/services/prompt-service`
- `pip install -r requirements.txt`
- Copy `env.example` → `.env` (hoặc đặt `DATABASE_URL`, `REDIS_URL`)
- `uvicorn app:app --host 0.0.0.0 --port 8000`

## Endpoints

- `POST /prompts` tạo prompt (key unique)
- `POST /prompts/{id}/versions` tạo version (validate placeholders)
- `GET /prompts/{id}?version=latest|<n>` đọc prompt + version (có cache Redis)
- `GET /metrics`

## Ghi chú

- Chạy Alembic nếu chưa có schema P2.
- Metrics: hit/miss/invalidate counters đã có.
