import os
import sys
from pathlib import Path
from dataclasses import dataclass

ai_core_path = Path(__file__).parent.parent.parent.parent
if str(ai_core_path) not in sys.path:
	sys.path.insert(0, str(ai_core_path))

from shared.config.model_hints import get_service_task_hint
from shared.config.service_configs import OrchestratorServiceConfig


_config_instance: OrchestratorServiceConfig | None = None


def _get_service_config() -> OrchestratorServiceConfig:
	global _config_instance
	if _config_instance is None:
		_config_instance = OrchestratorServiceConfig.from_env()
	return _config_instance


@dataclass(frozen=True)
class OrchestratorConfig:
	service_config: OrchestratorServiceConfig
	summary_model_hint: str
	sentiment_model_hint: str
	implication_model_hint: str
	argument_claim_model_hint: str
	argument_reason_model_hint: str
	logic_bias_model_hint: str

	@staticmethod
	def from_env() -> "OrchestratorConfig":
		service_config = OrchestratorServiceConfig.from_env()
		service = "orchestrator"
		return OrchestratorConfig(
			service_config=service_config,
			summary_model_hint=os.getenv("SUMMARY_MODEL_HINT") or get_service_task_hint("summary", service),
			sentiment_model_hint=os.getenv("SENTIMENT_MODEL_HINT") or get_service_task_hint("sentiment", service),
			implication_model_hint=os.getenv("IMPLICATION_MODEL_HINT") or get_service_task_hint("implication", service),
			argument_claim_model_hint=os.getenv("ARGUMENT_CLAIM_MODEL_HINT") or get_service_task_hint("claim", service),
			argument_reason_model_hint=os.getenv("ARGUMENT_REASON_MODEL_HINT") or get_service_task_hint("reason", service),
			logic_bias_model_hint=os.getenv("LOGIC_BIAS_MODEL_HINT") or get_service_task_hint("logic_bias", service),
		)


_service_config = _get_service_config()

DATABASE_URL = _service_config.database_url
MODEL_ADAPTER_BASE_URL = _service_config.model_adapter_base_url
PROMPT_SERVICE_BASE_URL = _service_config.prompt_service_base_url
KAFKA_BOOTSTRAP = _service_config.kafka_bootstrap
KAFKA_GROUP = _service_config.kafka_group
TOPIC_TASKS = _service_config.topic_tasks
TOPIC_DLQ = _service_config.topic_dlq
WORKER_TIMEOUT_SEC = _service_config.worker_timeout_sec
WORKER_MAX_RETRY = _service_config.worker_max_retry
ORCHESTRATOR_MAX_RETRY = _service_config.orchestrator_max_retry
