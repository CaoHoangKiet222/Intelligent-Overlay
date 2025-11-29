import os
from dataclasses import dataclass


@dataclass(frozen=True)
class HTTPTimeoutConfig:
	connect: float
	read: float
	write: float
	total: float

	@staticmethod
	def from_env(prefix: str = "") -> "HTTPTimeoutConfig":
		env_prefix = f"{prefix}_" if prefix else ""
		return HTTPTimeoutConfig(
			connect=float(os.getenv(f"{env_prefix}HTTP_CONNECT_TIMEOUT", "120.0")),
			read=float(os.getenv(f"{env_prefix}HTTP_READ_TIMEOUT", "120.0")),
			write=float(os.getenv(f"{env_prefix}HTTP_WRITE_TIMEOUT", "120.0")),
			total=float(os.getenv(f"{env_prefix}HTTP_TOTAL_TIMEOUT", "120.0")),
		)

	def to_httpx_timeout(self):
		import httpx
		return httpx.Timeout(
			timeout=self.total,
			connect=self.connect,
			read=self.read,
			write=self.write,
		)

	def to_httpx_simple_timeout(self) -> float:
		return self.total


@dataclass(frozen=True)
class ServiceTimeoutConfig:
	model_adapter: float
	prompt_service: float
	retrieval_service: float
	agent_service: float
	orchestrator: float

	@staticmethod
	def from_env() -> "ServiceTimeoutConfig":
		return ServiceTimeoutConfig(
			model_adapter=float(os.getenv("MODEL_ADAPTER_TIMEOUT", "120.0")),
			prompt_service=float(os.getenv("PROMPT_SERVICE_TIMEOUT", "120.0")),
			retrieval_service=float(os.getenv("RETRIEVAL_SERVICE_TIMEOUT", "120.0")),
			agent_service=float(os.getenv("AGENT_SERVICE_TIMEOUT", "120.0")),
			orchestrator=float(os.getenv("ORCHESTRATOR_TIMEOUT", "120.0")),
		)


@dataclass(frozen=True)
class WorkerTimeoutConfig:
	orchestrator_worker: float
	realtime_worker: float
	retrieval_context: float
	retrieval_search: float

	@staticmethod
	def from_env() -> "WorkerTimeoutConfig":
		return WorkerTimeoutConfig(
			orchestrator_worker=float(os.getenv("WORKER_TIMEOUT_SEC", "120")),
			realtime_worker=float(os.getenv("REALTIME_WORKER_TIMEOUT", "120.0")),
			retrieval_context=float(os.getenv("RETRIEVAL_CONTEXT_TIMEOUT", "120.0")),
			retrieval_search=float(os.getenv("RETRIEVAL_SEARCH_TIMEOUT", "120.0")),
		)


@dataclass(frozen=True)
class ProviderTimeoutConfig:
	ollama_total: float
	ollama_connect: float
	openai_total: float
	openai_connect: float

	@staticmethod
	def from_env() -> "ProviderTimeoutConfig":
		return ProviderTimeoutConfig(
			ollama_total=float(os.getenv("OLLAMA_TOTAL_TIMEOUT", "120.0")),
			ollama_connect=float(os.getenv("OLLAMA_CONNECT_TIMEOUT", "120.0")),
			openai_total=float(os.getenv("OPENAI_TOTAL_TIMEOUT", "120.0")),
			openai_connect=float(os.getenv("OPENAI_CONNECT_TIMEOUT", "120.0")),
		)

	def get_ollama_timeout(self):
		import httpx
		return httpx.Timeout(self.ollama_total, connect=self.ollama_connect)

	def get_openai_timeout(self):
		import httpx
		return httpx.Timeout(self.openai_total, connect=self.openai_connect)


@dataclass(frozen=True)
class TimeoutConfig:
	http_default: HTTPTimeoutConfig
	http_model_adapter: HTTPTimeoutConfig
	http_prompt_service: HTTPTimeoutConfig
	http_retrieval_service: HTTPTimeoutConfig
	http_agent_service: HTTPTimeoutConfig
	http_orchestrator: HTTPTimeoutConfig
	services: ServiceTimeoutConfig
	workers: WorkerTimeoutConfig
	providers: ProviderTimeoutConfig

	@staticmethod
	def from_env() -> "TimeoutConfig":
		return TimeoutConfig(
			http_default=HTTPTimeoutConfig.from_env(),
			http_model_adapter=HTTPTimeoutConfig.from_env("MODEL_ADAPTER"),
			http_prompt_service=HTTPTimeoutConfig.from_env("PROMPT_SERVICE"),
			http_retrieval_service=HTTPTimeoutConfig.from_env("RETRIEVAL_SERVICE"),
			http_agent_service=HTTPTimeoutConfig.from_env("AGENT_SERVICE"),
			http_orchestrator=HTTPTimeoutConfig.from_env("ORCHESTRATOR"),
			services=ServiceTimeoutConfig.from_env(),
			workers=WorkerTimeoutConfig.from_env(),
			providers=ProviderTimeoutConfig.from_env(),
		)


_timeout_config_instance: TimeoutConfig | None = None


def get_timeout_config() -> TimeoutConfig:
	global _timeout_config_instance
	if _timeout_config_instance is None:
		_timeout_config_instance = TimeoutConfig.from_env()
	return _timeout_config_instance

