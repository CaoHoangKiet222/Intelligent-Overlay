import os
import sys
from pathlib import Path

ai_core_path = Path(__file__).parent.parent.parent.parent
if str(ai_core_path) not in sys.path:
	sys.path.insert(0, str(ai_core_path))

from shared.config.service_configs import DemoApiConfig


class DemoConfig:
	def __init__(self) -> None:
		service_config = DemoApiConfig.from_env()
		self.model_adapter_base_url = service_config.model_adapter_base_url
		self.prompt_service_base_url = service_config.prompt_service_base_url
		self.retrieval_service_base_url = service_config.retrieval_service_base_url
		self.orchestrator_base_url = service_config.orchestrator_base_url
		self.agent_service_base_url = service_config.agent_service_base_url
		self.use_agent_service = service_config.use_agent_service
		self.kafka_bootstrap = service_config.kafka_bootstrap
		self.topic_tasks = service_config.topic_tasks
		self.context_segment_limit = service_config.context_segment_limit
		self.qa_top_k = service_config.qa_top_k
		self.prompt_cache_ttl_sec = service_config.prompt_cache_ttl_sec
		self.provider_hint = service_config.provider_hint
		self.summary_prompt_key = os.getenv("SUMMARY_PROMPT_KEY", "demo.summary.v1")
		self.argument_prompt_key = os.getenv("ARGUMENT_PROMPT_KEY", "demo.argument.v1")
		self.implication_prompt_key = os.getenv("IMPLICATION_PROMPT_KEY", "demo.implication.v1")
		self.sentiment_prompt_key = os.getenv("SENTIMENT_PROMPT_KEY", "demo.sentiment.v1")
		self.logic_bias_prompt_key = os.getenv("LOGIC_BIAS_PROMPT_KEY", "demo.logic_bias.v1")
		self.qa_prompt_key = os.getenv("QA_PROMPT_KEY", "demo.qa.v1")

	def worker_prompt_keys(self) -> dict[str, str]:
		return {
			"summary": self.summary_prompt_key,
			"argument": self.argument_prompt_key,
			"implication": self.implication_prompt_key,
			"sentiment": self.sentiment_prompt_key,
			"logic_bias": self.logic_bias_prompt_key,
		}

