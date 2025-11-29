# Centralized Environment Variables Example

File này mô tả tất cả environment variables có thể được sử dụng trong hệ thống.

## Quick Start

Copy file này thành `.env` ở root của project và điều chỉnh theo nhu cầu:

```bash
cp ai-core/shared/config/ENV_EXAMPLE.md .env
```

## Base Configuration

### Database
```bash
# Option 1: Set individual components
DB_USER=ai
DB_PASSWORD=ai
DB_NAME=ai_core
DB_HOST=postgres
DB_PORT=5432

# Option 2: Set full connection strings (overrides individual components)
DATABASE_URL=postgresql+asyncpg://ai:ai@postgres:5432/ai_core
DB_DSN=postgresql+psycopg://ai:ai@postgres:5432/ai_core
```

### Redis
```bash
# Option 1: Set individual components
REDIS_HOST=redis
REDIS_PORT=6379

# Option 2: Set full URL (overrides individual components)
REDIS_URL=redis://redis:6379/0
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
OLLAMA_NUM_GPU=
OLLAMA_GPU_ENABLED=true
```

### Service URLs
```bash
# Model Adapter
MODEL_ADAPTER_HOST=model-adapter
MODEL_ADAPTER_PORT=8000
MODEL_ADAPTER_BASE_URL=http://model-adapter:8000

# Prompt Service
PROMPT_SERVICE_HOST=prompt-service
PROMPT_SERVICE_PORT=8000
PROMPT_SERVICE_BASE_URL=http://prompt-service:8000

# Retrieval Service
RETRIEVAL_SERVICE_HOST=retrieval-service
RETRIEVAL_SERVICE_PORT=8000
RETRIEVAL_SERVICE_BASE_URL=http://retrieval-service:8000

# Orchestrator
ORCHESTRATOR_HOST=orchestrator
ORCHESTRATOR_PORT=8000
ORCHESTRATOR_BASE_URL=http://orchestrator:8000

# Agent Service
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

## Model Hints Configuration

```bash
# Global default
MODEL_HINT_DEFAULT=ollama

# Task-specific defaults (JSON)
MODEL_HINT_TASK_DEFAULTS={"summary":"ollama","qa":"ollama","argument":"ollama","logic_bias":"ollama","sentiment":"ollama","planner":"ollama","answer":"ollama","implication":"ollama","claim":"ollama","reason":"ollama"}

# Service-specific overrides (JSON)
MODEL_HINT_SERVICE_OVERRIDES={}
```

## Service-Specific Configuration

### Model Adapter
```bash
PROVIDER_KEYS={"ollama":"ollama"}
TASK_ROUTING={}
```

### Retrieval Service
```bash
EMBED_MODEL_HINT=ollama
EMBEDDING_DIM=1024
SEARCH_ALPHA=0.7
VEC_CANDIDATES=100
TRGM_CANDIDATES=200
TOP_K=10
```

### Timeout Configuration
```bash
# HTTP Default Timeouts (default: 120.0s)
HTTP_CONNECT_TIMEOUT=120.0
HTTP_READ_TIMEOUT=120.0
HTTP_WRITE_TIMEOUT=120.0
HTTP_TOTAL_TIMEOUT=120.0

# Service-specific HTTP Timeouts (optional, overrides defaults)
MODEL_ADAPTER_HTTP_CONNECT_TIMEOUT=120.0
MODEL_ADAPTER_HTTP_READ_TIMEOUT=120.0
MODEL_ADAPTER_HTTP_WRITE_TIMEOUT=120.0
MODEL_ADAPTER_HTTP_TOTAL_TIMEOUT=120.0

PROMPT_SERVICE_HTTP_CONNECT_TIMEOUT=120.0
PROMPT_SERVICE_HTTP_READ_TIMEOUT=120.0
PROMPT_SERVICE_HTTP_WRITE_TIMEOUT=120.0
PROMPT_SERVICE_HTTP_TOTAL_TIMEOUT=120.0

RETRIEVAL_SERVICE_HTTP_CONNECT_TIMEOUT=120.0
RETRIEVAL_SERVICE_HTTP_READ_TIMEOUT=120.0
RETRIEVAL_SERVICE_HTTP_WRITE_TIMEOUT=120.0
RETRIEVAL_SERVICE_HTTP_TOTAL_TIMEOUT=120.0

AGENT_SERVICE_HTTP_CONNECT_TIMEOUT=120.0
AGENT_SERVICE_HTTP_READ_TIMEOUT=120.0
AGENT_SERVICE_HTTP_WRITE_TIMEOUT=120.0
AGENT_SERVICE_HTTP_TOTAL_TIMEOUT=120.0

ORCHESTRATOR_HTTP_CONNECT_TIMEOUT=120.0
ORCHESTRATOR_HTTP_READ_TIMEOUT=120.0
ORCHESTRATOR_HTTP_WRITE_TIMEOUT=120.0
ORCHESTRATOR_HTTP_TOTAL_TIMEOUT=120.0

# Service Timeouts (simple float values for backward compatibility, default: 120.0s)
MODEL_ADAPTER_TIMEOUT=120.0
PROMPT_SERVICE_TIMEOUT=120.0
RETRIEVAL_SERVICE_TIMEOUT=120.0
AGENT_SERVICE_TIMEOUT=120.0
ORCHESTRATOR_TIMEOUT=120.0

# Worker Timeouts (default: 120.0s)
WORKER_TIMEOUT_SEC=120
REALTIME_WORKER_TIMEOUT=120.0
RETRIEVAL_CONTEXT_TIMEOUT=120.0
RETRIEVAL_SEARCH_TIMEOUT=120.0

# Provider Timeouts (default: 120.0s)
OLLAMA_TOTAL_TIMEOUT=120.0
OLLAMA_CONNECT_TIMEOUT=120.0
OPENAI_TOTAL_TIMEOUT=120.0
OPENAI_CONNECT_TIMEOUT=120.0
```

### Orchestrator Service
```bash
WORKER_MAX_RETRY=2
ORCHESTRATOR_MAX_RETRY=1

# Model hints (optional, uses centralized config if not set)
SUMMARY_MODEL_HINT=
SENTIMENT_MODEL_HINT=
IMPLICATION_MODEL_HINT=
ARGUMENT_CLAIM_MODEL_HINT=
ARGUMENT_REASON_MODEL_HINT=
LOGIC_BIAS_MODEL_HINT=
```

### Agent Service
```bash
# Model hints (optional, uses centralized config if not set)
AGENT_PLANNER_MODEL_HINT=
AGENT_ANSWER_MODEL_HINT=
```

### Demo API
```bash
USE_AGENT_SERVICE=true
CONTEXT_SEGMENT_LIMIT=12
QA_TOP_K=4
PROMPT_CACHE_TTL_SEC=300
MODEL_PROVIDER_HINT=

# Prompt keys
SUMMARY_PROMPT_KEY=demo.summary.v1
ARGUMENT_PROMPT_KEY=demo.argument.v1
IMPLICATION_PROMPT_KEY=demo.implication.v1
SENTIMENT_PROMPT_KEY=demo.sentiment.v1
LOGIC_BIAS_PROMPT_KEY=demo.logic_bias.v1
QA_PROMPT_KEY=demo.qa.v1
```

### Prompt Service
```bash
PROMPT_CACHE_TTL_SECONDS=86400
```

## Port Configuration

```bash
PORT=8000
```

## Fallback Strategy

Hệ thống sử dụng fallback hierarchy:

1. **Direct env var** (nếu set, ví dụ: `DATABASE_URL`)
2. **Host/Port vars** (ví dụ: `DB_HOST` + `DB_PORT` → tạo connection string)
3. **Defaults** (hardcoded trong BaseConfig)

## Examples

### Minimal Configuration (Docker Compose)
```bash
# Chỉ cần set những gì khác với defaults
MODEL_HINT_DEFAULT=ollama
PROVIDER_KEYS={"ollama":"ollama"}
```

### Full Custom Configuration
```bash
# Database
DB_USER=myuser
DB_PASSWORD=mypass
DB_NAME=mydb
DB_HOST=my-postgres
DB_PORT=5432

# Redis
REDIS_HOST=my-redis
REDIS_PORT=6380

# Ollama
OLLAMA_HOST=my-ollama
OLLAMA_PORT=11434
OLLAMA_GENERATION_MODEL=qwen2.5:1.5b

# Model Hints
MODEL_HINT_DEFAULT=ollama
MODEL_HINT_SERVICE_OVERRIDES={"orchestrator":{"summary":"openai"}}
```

