import os
from dataclasses import dataclass
from typing import Optional
from .base import get_base_config


@dataclass(frozen=True)
class RetrievalServiceConfig:
	database_url: str
	model_adapter_base_url: str
	embed_model_hint: str
	embedding_dim: int
	redis_url: str
	search_alpha: float
	vec_candidates: int
	trgm_candidates: int
	top_k: int
	
	@staticmethod
	def from_env() -> "RetrievalServiceConfig":
		base = get_base_config()
		return RetrievalServiceConfig(
			database_url=base.database_url,
			model_adapter_base_url=base.model_adapter_base_url,
			embed_model_hint=os.getenv("EMBED_MODEL_HINT", "ollama"),
			embedding_dim=int(os.getenv("EMBEDDING_DIM", "1024")),
			redis_url=base.redis_url,
			search_alpha=float(os.getenv("SEARCH_ALPHA", "0.7")),
			vec_candidates=int(os.getenv("VEC_CANDIDATES", "100")),
			trgm_candidates=int(os.getenv("TRGM_CANDIDATES", "200")),
			top_k=int(os.getenv("TOP_K", "10")),
		)


@dataclass(frozen=True)
class OrchestratorServiceConfig:
	database_url: str
	model_adapter_base_url: str
	prompt_service_base_url: str
	ray_address: str
	ray_num_cpus: int
	ray_num_gpus: int
	redis_url: str
	kafka_bootstrap: str
	kafka_group: str
	topic_tasks: str
	topic_dlq: str
	worker_timeout_sec: int
	worker_max_retry: int
	orchestrator_max_retry: int
	
	@staticmethod
	def from_env() -> "OrchestratorServiceConfig":
		base = get_base_config()
		return OrchestratorServiceConfig(
			database_url=base.database_url,
			model_adapter_base_url=base.model_adapter_base_url,
			prompt_service_base_url=base.prompt_service_base_url,
			ray_address=base.ray_address if base.ray_address else f"{os.getenv('RAY_HOST', 'ray-head')}:{os.getenv('RAY_PORT', '6380')}",
			ray_num_cpus=base.ray_num_cpus,
			ray_num_gpus=base.ray_num_gpus,
			redis_url=base.redis_url,
			kafka_bootstrap=base.kafka_bootstrap,
			kafka_group=base.kafka_group,
			topic_tasks=base.topic_tasks,
			topic_dlq=base.topic_dlq,
			worker_timeout_sec=int(os.getenv("WORKER_TIMEOUT_SEC", "20")),
			worker_max_retry=int(os.getenv("WORKER_MAX_RETRY", "2")),
			orchestrator_max_retry=int(os.getenv("ORCHESTRATOR_MAX_RETRY", "1")),
		)


@dataclass(frozen=True)
class ModelAdapterConfig:
	database_dsn: str
	redis_url: str
	s3_endpoint: str
	s3_access_key: str
	s3_secret_key: str
	prompt_service_base_url: str
	ollama_base_url: str
	ollama_generation_model: str
	ollama_embedding_model: str
	provider_keys: dict
	task_routing: dict
	
	@staticmethod
	def from_env() -> "ModelAdapterConfig":
		import json
		base = get_base_config()
		
		provider_keys_raw = os.getenv("PROVIDER_KEYS", "{}")
		try:
			provider_keys = json.loads(provider_keys_raw)
		except Exception:
			provider_keys = {}
		
		task_routing_raw = os.getenv("TASK_ROUTING", "{}")
		try:
			task_routing = json.loads(task_routing_raw)
		except Exception:
			task_routing = {}
		
		return ModelAdapterConfig(
			database_dsn=base.database_dsn,
			redis_url=base.redis_url,
			s3_endpoint=base.s3_endpoint,
			s3_access_key=base.s3_access_key,
			s3_secret_key=base.s3_secret_key,
			prompt_service_base_url=base.prompt_service_base_url,
			ollama_base_url=base.ollama_base_url,
			ollama_generation_model=base.ollama_generation_model,
			ollama_embedding_model=base.ollama_embedding_model,
			provider_keys=provider_keys,
			task_routing=task_routing,
		)


@dataclass(frozen=True)
class AgentServiceConfig:
	redis_url: str
	ray_address: str
	model_adapter_base_url: str
	retrieval_service_base_url: str
	planner_model_hint: str
	answer_model_hint: str
	
	@staticmethod
	def from_env() -> "AgentServiceConfig":
		from .model_hints import get_service_task_hint
		base = get_base_config()
		
		service = "agent"
		return AgentServiceConfig(
			redis_url=base.redis_url,
			ray_address=base.ray_address if base.ray_address else f"{os.getenv('RAY_HOST', 'ray-head')}:{os.getenv('RAY_PORT', '6379')}",
			model_adapter_base_url=base.model_adapter_base_url,
			retrieval_service_base_url=base.retrieval_service_base_url,
			planner_model_hint=os.getenv("AGENT_PLANNER_MODEL_HINT") or get_service_task_hint("planner", service),
			answer_model_hint=os.getenv("AGENT_ANSWER_MODEL_HINT") or get_service_task_hint("answer", service),
		)


@dataclass(frozen=True)
class DemoApiConfig:
	model_adapter_base_url: str
	prompt_service_base_url: str
	retrieval_service_base_url: str
	orchestrator_base_url: str
	agent_service_base_url: str
	use_agent_service: bool
	kafka_bootstrap: str
	topic_tasks: str
	context_segment_limit: int
	qa_top_k: int
	prompt_cache_ttl_sec: int
	provider_hint: str
	
	@staticmethod
	def from_env() -> "DemoApiConfig":
		from .model_hints import get_service_task_hint
		base = get_base_config()
		
		return DemoApiConfig(
			model_adapter_base_url=base.model_adapter_base_url,
			prompt_service_base_url=base.prompt_service_base_url,
			retrieval_service_base_url=base.retrieval_service_base_url,
			orchestrator_base_url=base.orchestrator_base_url,
			agent_service_base_url=base.agent_service_base_url,
			use_agent_service=os.getenv("USE_AGENT_SERVICE", "true").lower() == "true",
			kafka_bootstrap=base.kafka_bootstrap,
			topic_tasks=base.topic_tasks,
			context_segment_limit=int(os.getenv("CONTEXT_SEGMENT_LIMIT", "12")),
			qa_top_k=int(os.getenv("QA_TOP_K", "4")),
			prompt_cache_ttl_sec=int(os.getenv("PROMPT_CACHE_TTL_SEC", "300")),
			provider_hint=os.getenv("MODEL_PROVIDER_HINT") or get_service_task_hint("qa", "demo"),
		)


@dataclass(frozen=True)
class PromptServiceConfig:
	database_dsn: str
	
	@staticmethod
	def from_env() -> "PromptServiceConfig":
		base = get_base_config()
		return PromptServiceConfig(
			database_dsn=base.database_dsn,
		)

