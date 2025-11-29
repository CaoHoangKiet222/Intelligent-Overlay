import os
from dataclasses import dataclass
from typing import Optional
from .timeout_config import TimeoutConfig, get_timeout_config


@dataclass(frozen=True)
class BaseConfig:
	database_url: str
	database_dsn: str
	redis_url: str
	redis_port: int
	
	kafka_bootstrap: str
	kafka_group: str
	kafka_port: int
	topic_tasks: str
	topic_dlq: str
	
	s3_endpoint: str
	s3_access_key: str
	s3_secret_key: str
	s3_port: int
	s3_console_port: int
	
	ollama_base_url: str
	ollama_generation_model: str
	ollama_embedding_model: str
	ollama_port: int
	
	model_adapter_base_url: str
	prompt_service_base_url: str
	retrieval_service_base_url: str
	orchestrator_base_url: str
	agent_service_base_url: str
	
	ray_address: str
	ray_num_cpus: int
	ray_num_gpus: int
	timeout_config: TimeoutConfig
	
	@staticmethod
	def from_env() -> "BaseConfig":
		db_user = os.getenv("DB_USER", "ai")
		db_password = os.getenv("DB_PASSWORD", "ai")
		db_name = os.getenv("DB_NAME", "ai_core")
		db_host = os.getenv("DB_HOST", "postgres")
		db_port = int(os.getenv("DB_PORT", "5432"))
		
		database_url = os.getenv("DATABASE_URL") or f"postgresql+asyncpg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
		database_dsn = os.getenv("DB_DSN") or f"postgresql+psycopg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
		
		redis_host = os.getenv("REDIS_HOST", "redis")
		redis_port = int(os.getenv("REDIS_PORT", "6379"))
		redis_url = os.getenv("REDIS_URL") or f"redis://{redis_host}:{redis_port}/0"
		
		kafka_host = os.getenv("KAFKA_HOST", "broker")
		kafka_port = int(os.getenv("KAFKA_PORT", "9092"))
		kafka_bootstrap = os.getenv("KAFKA_BOOTSTRAP") or f"{kafka_host}:{kafka_port}"
		
		ollama_host = os.getenv("OLLAMA_HOST", "ollama")
		ollama_port = int(os.getenv("OLLAMA_PORT", "11434"))
		ollama_base_url = os.getenv("OLLAMA_BASE_URL") or f"http://{ollama_host}:{ollama_port}/api"
		
		model_adapter_host = os.getenv("MODEL_ADAPTER_HOST", "model-adapter")
		model_adapter_port = int(os.getenv("MODEL_ADAPTER_PORT", "8000"))
		model_adapter_base_url = os.getenv("MODEL_ADAPTER_BASE_URL") or f"http://{model_adapter_host}:{model_adapter_port}"
		
		prompt_service_host = os.getenv("PROMPT_SERVICE_HOST", "prompt-service")
		prompt_service_port = int(os.getenv("PROMPT_SERVICE_PORT", "8000"))
		prompt_service_base_url = os.getenv("PROMPT_SERVICE_BASE_URL") or f"http://{prompt_service_host}:{prompt_service_port}"
		
		retrieval_service_host = os.getenv("RETRIEVAL_SERVICE_HOST", "retrieval-service")
		retrieval_service_port = int(os.getenv("RETRIEVAL_SERVICE_PORT", "8000"))
		retrieval_service_base_url = os.getenv("RETRIEVAL_SERVICE_BASE_URL") or f"http://{retrieval_service_host}:{retrieval_service_port}"
		
		orchestrator_host = os.getenv("ORCHESTRATOR_HOST", "orchestrator")
		orchestrator_port = int(os.getenv("ORCHESTRATOR_PORT", "8000"))
		orchestrator_base_url = os.getenv("ORCHESTRATOR_BASE_URL") or f"http://{orchestrator_host}:{orchestrator_port}"
		
		agent_service_host = os.getenv("AGENT_SERVICE_HOST", "agent-service")
		agent_service_port = int(os.getenv("AGENT_SERVICE_PORT", "8000"))
		agent_service_base_url = os.getenv("AGENT_SERVICE_BASE_URL") or f"http://{agent_service_host}:{agent_service_port}"
		
		s3_host = os.getenv("S3_HOST", "minio")
		s3_port = int(os.getenv("S3_PORT", "9000"))
		s3_console_port = int(os.getenv("S3_CONSOLE_PORT", "9001"))
		s3_endpoint = os.getenv("S3_ENDPOINT") or f"http://{s3_host}:{s3_port}"
		
		return BaseConfig(
			database_url=database_url,
			database_dsn=database_dsn,
			redis_url=redis_url,
			redis_port=redis_port,
			kafka_bootstrap=kafka_bootstrap,
			kafka_group=os.getenv("KAFKA_GROUP", "aicore-orchestrator"),
			kafka_port=kafka_port,
			topic_tasks=os.getenv("TOPIC_TASKS", "analysis.tasks"),
			topic_dlq=os.getenv("TOPIC_DLQ", "analysis.dlq"),
			s3_endpoint=s3_endpoint,
			s3_access_key=os.getenv("S3_ACCESS_KEY", "minioadmin"),
			s3_secret_key=os.getenv("S3_SECRET_KEY", "minioadmin"),
			s3_port=s3_port,
			s3_console_port=s3_console_port,
			ollama_base_url=ollama_base_url,
			ollama_generation_model=os.getenv("OLLAMA_GENERATION_MODEL", "phi3:mini"),
			ollama_embedding_model=os.getenv("OLLAMA_EMBEDDING_MODEL", "qwen3-embedding:0.6b"),
			ollama_port=ollama_port,
			model_adapter_base_url=model_adapter_base_url,
			prompt_service_base_url=prompt_service_base_url,
			retrieval_service_base_url=retrieval_service_base_url,
			orchestrator_base_url=orchestrator_base_url,
			agent_service_base_url=agent_service_base_url,
			ray_address=os.getenv("RAY_ADDRESS", ""),
			ray_num_cpus=int(os.getenv("RAY_NUM_CPUS", "2")),
			ray_num_gpus=int(os.getenv("RAY_NUM_GPUS", "0")),
			timeout_config=get_timeout_config(),
		)


_config_instance: Optional[BaseConfig] = None


def get_base_config() -> BaseConfig:
	global _config_instance
	if _config_instance is None:
		_config_instance = BaseConfig.from_env()
	return _config_instance

