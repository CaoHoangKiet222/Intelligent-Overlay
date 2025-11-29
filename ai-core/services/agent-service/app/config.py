import sys
from pathlib import Path

ai_core_path = Path(__file__).parent.parent.parent.parent
if str(ai_core_path) not in sys.path:
	sys.path.insert(0, str(ai_core_path))

from shared.config.service_configs import AgentServiceConfig


class AgentConfig:
	planner_model_hint: str
	answer_model_hint: str
	redis_url: str
	ray_address: str
	model_adapter_base_url: str
	retrieval_service_base_url: str

	@staticmethod
	def from_env() -> "AgentConfig":
		service_config = AgentServiceConfig.from_env()
		config = AgentConfig.__new__(AgentConfig)
		config.planner_model_hint = service_config.planner_model_hint
		config.answer_model_hint = service_config.answer_model_hint
		config.redis_url = service_config.redis_url
		config.ray_address = service_config.ray_address
		config.model_adapter_base_url = service_config.model_adapter_base_url
		config.retrieval_service_base_url = service_config.retrieval_service_base_url
		return config

