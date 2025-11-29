# AI Core Monorepo — Hướng dẫn chạy nhanh

## Yêu cầu môi trường

- Docker + Docker Compose (khuyến nghị)
- Python 3.11+ (nếu chạy local từng service)
- Kafka (nếu chạy orchestrator service local - có thể dùng Docker: `docker compose up zookeeper broker -d`)
- NVIDIA GPU với CUDA (khuyến nghị cho Ollama, có thể chạy CPU-only nhưng chậm hơn)

## Khởi động toàn bộ bằng Docker Compose

1. Sao chép file env mẫu (tùy chọn):

- `cp ai-core/env.example .env` (hoặc tự đặt biến môi trường)

2. Chạy:

- `docker compose up -d --build`

3. Kiểm tra health:

- Ollama: `curl http://localhost:11434/api/tags` (hoặc `docker logs ai_core_ollama_init` để xem models đã được preload)
- Model Adapter: `curl http://localhost:8081/healthz`
- Prompt Service: `curl http://localhost:8082/healthz`
- Retrieval Service: `curl http://localhost:8083/healthz`
- Agent Service: `curl http://localhost:8084/healthz`
- Orchestrator: `curl http://localhost:8085/healthz`
- Kafka: `docker exec ai_core_kafka kafka-broker-api-versions --bootstrap-server localhost:9092`

4. Kiểm tra Ollama models đã được preload:

```bash
# Xem logs của ollama-init service
docker logs ai_core_ollama_init

# Kiểm tra models có sẵn
curl http://localhost:11434/api/tags

# Kiểm tra model-adapter có thể giao tiếp với Ollama
curl http://localhost:8081/providers
```

5. Migrations (nếu cần):

- Prompt/Retrieval/Orchestrator dùng schema từ P2/P6. Chạy Alembic tại thư mục migrations tương ứng hoặc tại `ai-core/db`:
- `cd ai-core/db`
- `python3 -m venv .venv`
- `source .venv/bin/activate`
- `pip install -r requirements.txt`
- `DB_DSN="postgresql+psycopg://ai:ai@localhost:5432/ai_core" alembic upgrade head`

## Services

- **Ollama** (LLM Runtime): Local LLM inference server với OpenAI-compatible API - Port 11434
  - Tự động preload các models: `phi3:mini`, `qwen3-embedding:0.6b`
  - Models được tối ưu cho GPU 4GB
  - Base URL: `http://ollama:11434/api` (internal) hoặc `http://localhost:11434/api` (external)
- **Model Adapter** (FastAPI): `ai-core/services/model-adapter` (POST /generate, POST /embed, GET /providers) - Port 8081
  - Hỗ trợ nhiều providers: OpenAI, Anthropic, Mistral, **Ollama**
  - Ollama provider sử dụng OpenAI-compatible API endpoint
- **Prompt Service** (FastAPI): `ai-core/services/prompt-service` (CRUD prompt/version + cache) - Port 8082
- **Retrieval Service** (FastAPI): `ai-core/services/retrieval-service` (POST /ingest, POST /search) - Port 8083
  - Sử dụng Ollama embeddings (qwen3-embedding:0.6b, 1024 dim) mặc định
- **Agent Service** (FastAPI + LangGraph): `ai-core/services/agent-service` (POST /agent/ask) - Port 8084
- **Orchestrator** (Kafka + Ray + FastAPI): `ai-core/services/orchestrator` - Port 8085
- **Demo API** (FastAPI): `ai-core/services/demo-api` (POST /demo/analyze, POST /demo/qa) - Port 8090

Mỗi service có README riêng hướng dẫn chạy local và endpoints.

## Cấu hình Ollama

### Models được sử dụng

- **phi3:mini**: Model chính cho generation tasks (~2.3GB), chất lượng tốt cho general purpose
- **qwen3-embedding:0.6b**: Embedding model chất lượng cao (1024 dim), tốt cho retrieval và semantic search

### Cấu hình môi trường

Tạo file `.env` từ `.env.example` và cấu hình:

```bash
# Ollama Configuration
OLLAMA_BASE_URL=http://ollama:11434/api
OLLAMA_GENERATION_MODEL=phi3:mini
OLLAMA_EMBEDDING_MODEL=qwen3-embedding:0.6b

# Model Adapter - Sử dụng Ollama làm provider mặc định
PROVIDER_KEYS={"ollama":"ollama"}
TASK_ROUTING={"summary":"ollama","qa":"ollama","argument":"ollama","logic_bias":"ollama","sentiment":"ollama"}

# Retrieval Service - Sử dụng Ollama embeddings
EMBED_MODEL_HINT=ollama
EMBEDDING_DIM=1024
```

### Chạy Ollama riêng lẻ

Nếu chỉ muốn chạy Ollama service:

```bash
# Chạy Ollama và preload models
docker compose up -d ollama ollama-init

# Xem logs
docker logs -f ai_core_ollama_init

# Test Ollama API
curl http://localhost:11434/api/tags
```

### Cấu hình GPU

#### NVIDIA GPU (Linux)
Ollama sẽ tự động phát hiện và sử dụng NVIDIA GPU nếu có NVIDIA Container Toolkit được cài đặt.

#### AMD/ROCm GPU (Linux)
Để sử dụng AMD GPU với ROCm, uncomment phần `devices` trong `docker-compose.yaml`:
```yaml
devices:
  - /dev/dri:/dev/dri
```

#### Apple Silicon GPU (macOS)
Docker trên macOS không hỗ trợ GPU passthrough. Để sử dụng Metal GPU:
1. Cài đặt Ollama native: `brew install ollama`
2. Chạy Ollama: `ollama serve`
3. Cập nhật `OLLAMA_BASE_URL` trong `.env` để trỏ đến `http://localhost:11434/api`
4. Comment out service `ollama` trong `docker-compose.yaml` hoặc không chạy nó

#### Chạy không có GPU (CPU only)
Nếu không có GPU, Ollama sẽ tự động chạy trên CPU (chậm hơn):
- Set environment variable: `OLLAMA_NUM_GPU=0` trong `.env`
- Hoặc để Ollama tự động phát hiện (mặc định sẽ dùng CPU nếu không tìm thấy GPU)

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
