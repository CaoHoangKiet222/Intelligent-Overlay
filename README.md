# AI Core Monorepo — Hướng dẫn chạy nhanh

## Yêu cầu môi trường

- Docker + Docker Compose (khuyến nghị)
- Python 3.11+ (nếu chạy local từng service)
- Kafka (nếu chạy orchestrator service local - có thể dùng Docker: `docker compose up zookeeper broker -d`)

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
- Kafka: `docker exec ai_core_kafka kafka-broker-api-versions --bootstrap-server localhost:9092`

4. Migrations (nếu cần):

- Prompt/Retrieval/Orchestrator dùng schema từ P2/P6. Chạy Alembic tại thư mục migrations tương ứng hoặc tại `ai-core/db`:
- `cd ai-core/db`
- `python3 -m venv .venv`
- `source .venv/bin/activate`
- `pip install -r requirements.txt`
- `DB_DSN="postgresql+psycopg://ai:ai@localhost:5432/ai_core" alembic upgrade head`

## Services

- Model Adapter (FastAPI): `ai-core/services/model-adapter` (POST /generate, POST /embed, GET /providers) - Port 8081
- Prompt Service (FastAPI): `ai-core/services/prompt-service` (CRUD prompt/version + cache) - Port 8082
- Retrieval Service (FastAPI): `ai-core/services/retrieval-service` (POST /ingest, POST /search) - Port 8083
- Agent Service (FastAPI + LangGraph): `ai-core/services/agent-service` (POST /agent/ask) - Port 8084
- Orchestrator (Kafka + Ray + FastAPI): `ai-core/services/orchestrator` - Port 8085

Mỗi service có README riêng hướng dẫn chạy local và endpoints.

## Chạy và kiểm tra services

### Chạy service

Sử dụng script `scripts/run_service.sh`:

```bash
# Chạy service (foreground - mặc định)
./scripts/run_service.sh orchestrator
./scripts/run_service.sh agent-service 8084

# Chạy service trên port tùy chỉnh
./scripts/run_service.sh orchestrator 8000

# Chạy service trong background
./scripts/run_service.sh orchestrator 8000 background

# Xem logs khi chạy background
tail -f /tmp/orchestrator.log
```

Khi chạy service, bạn sẽ thấy log:

```
INFO: Starting Orchestrator Service on port 8000
INFO: Health check: http://localhost:8000/healthz
INFO: Metrics: http://localhost:8000/metrics
```

### Kiểm tra trạng thái services

Sử dụng script kiểm tra:

```bash
# Kiểm tra tất cả services
./scripts/check_service.sh all

# Kiểm tra service cụ thể
./scripts/check_service.sh orchestrator 8000

# Kiểm tra thủ công
curl http://localhost:8000/healthz
lsof -ti:8000  # Tìm process đang dùng port
```

### Dừng service

Sử dụng script `scripts/kill_service.sh`:

```bash
# Dừng tất cả services
./scripts/kill_service.sh all

# Dừng service cụ thể
./scripts/kill_service.sh orchestrator
./scripts/kill_service.sh agent-service 8084

# Dừng service trên port tùy chỉnh
./scripts/kill_service.sh orchestrator 8000

# Dừng thủ công
kill $(lsof -ti:8000)  # Kill process trên port
```

**Lưu ý:** Script sẽ thử dừng gracefully trước, nếu không được sẽ force kill.

## Telemetry (tùy chọn)

- /metrics (Prometheus) đã mount trong các service chính.
- OpenTelemetry: đặt `SERVICE_NAME` và `OTLP_ENDPOINT` để bật traces.
- Logger JSON cho Loki (Promtail) đã cấu hình trong code; đảm bảo `LOG_LEVEL` phù hợp.

# Intelligent-Overlay
