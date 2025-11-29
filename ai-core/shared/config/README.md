# Centralized Configuration System

Hệ thống cấu hình tập trung cho tất cả services trong AI Core stack.

## Cấu trúc

Hệ thống sử dụng 3 lớp cấu hình:

1. **BaseConfig**: Cấu hình chung cho tất cả services (database, redis, kafka, s3, ollama, service URLs, ray)
2. **ServiceConfigs**: Cấu hình riêng cho từng service
3. **ModelHintsConfig**: Cấu hình model hints với fallback hierarchy

## Base Configuration

### Database
```bash
DB_USER=ai
DB_PASSWORD=ai
DB_NAME=ai_core
DB_HOST=postgres
DB_PORT=5432
# Hoặc override trực tiếp:
DATABASE_URL=postgresql+asyncpg://user:pass@host:port/db
DB_DSN=postgresql+psycopg://user:pass@host:port/db
```

### Redis
```bash
REDIS_HOST=redis
REDIS_PORT=6379
# Hoặc override:
REDIS_URL=redis://host:port/0
```

### Kafka
```bash
KAFKA_HOST=broker
KAFKA_PORT=9092
KAFKA_BOOTSTRAP=broker:9092
KAFKA_GROUP=aicore-orchestrator
TOPIC_TASKS=analysis.tasks
TOPIC_DLQ=analysis.dlq
```

### S3/MinIO
```bash
S3_HOST=minio
S3_PORT=9000
S3_CONSOLE_PORT=9001
S3_ENDPOINT=http://minio:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
```

### Ollama
```bash
OLLAMA_HOST=ollama
OLLAMA_PORT=11434
OLLAMA_BASE_URL=http://ollama:11434/api
OLLAMA_GENERATION_MODEL=phi3:mini
OLLAMA_EMBEDDING_MODEL=qwen3-embedding:0.6b
```

### Service URLs
```bash
# Có thể set từng service riêng hoặc dùng defaults
MODEL_ADAPTER_HOST=model-adapter
MODEL_ADAPTER_PORT=8000
MODEL_ADAPTER_BASE_URL=http://model-adapter:8000

PROMPT_SERVICE_HOST=prompt-service
PROMPT_SERVICE_PORT=8000
PROMPT_SERVICE_BASE_URL=http://prompt-service:8000

RETRIEVAL_SERVICE_HOST=retrieval-service
RETRIEVAL_SERVICE_PORT=8000
RETRIEVAL_SERVICE_BASE_URL=http://retrieval-service:8000

ORCHESTRATOR_HOST=orchestrator
ORCHESTRATOR_PORT=8000
ORCHESTRATOR_BASE_URL=http://orchestrator:8000

AGENT_SERVICE_HOST=agent-service
AGENT_SERVICE_PORT=8000
AGENT_SERVICE_BASE_URL=http://agent-service:8000
```

### Ray
```bash
RAY_HOST=ray-head
RAY_PORT=6380
RAY_ADDRESS=ray-head:6380
RAY_NUM_CPUS=2
RAY_NUM_GPUS=0
```

## Service-Specific Configuration

### Retrieval Service
```bash
EMBED_MODEL_HINT=ollama
EMBEDDING_DIM=1024
SEARCH_ALPHA=0.7
VEC_CANDIDATES=100
TRGM_CANDIDATES=200
TOP_K=10
```

### Orchestrator Service
```bash
WORKER_TIMEOUT_SEC=20
WORKER_MAX_RETRY=2
ORCHESTRATOR_MAX_RETRY=1
```

### Model Adapter
```bash
PROVIDER_KEYS={"ollama":"ollama"}
TASK_ROUTING={}
```

### Agent Service
```bash
AGENT_PLANNER_MODEL_HINT=
AGENT_ANSWER_MODEL_HINT=
```

### Demo API
```bash
USE_AGENT_SERVICE=true
CONTEXT_SEGMENT_LIMIT=12
QA_TOP_K=4
PROMPT_CACHE_TTL_SEC=300
```

## Model Hints Configuration

Xem [Model Hints README](./README.md) để biết chi tiết về cấu hình model hints.

## Usage trong Code

### Sử dụng BaseConfig
```python
from shared.config.base import get_base_config

config = get_base_config()
print(config.database_url)
print(config.redis_url)
print(config.ollama_base_url)
```

### Sử dụng ServiceConfigs
```python
from shared.config.service_configs import RetrievalServiceConfig

config = RetrievalServiceConfig.from_env()
print(config.database_url)
print(config.embedding_dim)
print(config.search_alpha)
```

### Fallback Hierarchy

1. **Direct env var** (nếu set, ví dụ: `DATABASE_URL`, `REDIS_URL`)
2. **Host/Port vars** (ví dụ: `DB_HOST`, `DB_PORT` → tạo connection string)
3. **Defaults** (hardcoded defaults trong BaseConfig)

## Benefits

1. **Centralized**: Tất cả config ở một nơi
2. **Flexible**: Có thể override ở nhiều cấp độ
3. **Type-safe**: Sử dụng dataclasses với type hints
4. **Consistent**: Tất cả services sử dụng cùng pattern
5. **Maintainable**: Dễ thêm/sửa config mới

## Migration

Tất cả services đã được migrate:
- ✅ Model Adapter
- ✅ Retrieval Service
- ✅ Orchestrator Service
- ✅ Agent Service
- ✅ Demo API
- ✅ Prompt Service

Legacy env vars vẫn được hỗ trợ để backward compatibility.
