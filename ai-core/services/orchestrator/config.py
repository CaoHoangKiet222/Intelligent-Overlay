import os

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "broker:9092")
KAFKA_GROUP = os.getenv("KAFKA_GROUP", "aicore-orchestrator")
TOPIC_TASKS = os.getenv("TOPIC_TASKS", "analysis.tasks")
TOPIC_DLQ = os.getenv("TOPIC_DLQ", "analysis.dlq")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://ai:ai@postgres:5432/ai_core")

MODEL_ADAPTER_BASE_URL = os.getenv("MODEL_ADAPTER_BASE_URL", "http://model-adapter:8000")
PROMPT_SERVICE_BASE_URL = os.getenv("PROMPT_SERVICE_BASE_URL", "http://prompt-service:8000")

RAY_ADDRESS = os.getenv("RAY_ADDRESS", "")
RAY_NUM_CPUS = int(os.getenv("RAY_NUM_CPUS", "2"))
RAY_NUM_GPUS = int(os.getenv("RAY_NUM_GPUS", "0"))

WORKER_TIMEOUT_SEC = int(os.getenv("WORKER_TIMEOUT_SEC", "20"))
WORKER_MAX_RETRY = int(os.getenv("WORKER_MAX_RETRY", "2"))
ORCHESTRATOR_MAX_RETRY = int(os.getenv("ORCHESTRATOR_MAX_RETRY", "1"))


