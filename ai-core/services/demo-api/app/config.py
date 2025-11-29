import os


class DemoConfig:
	def __init__(self) -> None:
		self.model_adapter_base_url = os.getenv("MODEL_ADAPTER_BASE_URL", "http://model-adapter:8000")
		self.prompt_service_base_url = os.getenv("PROMPT_SERVICE_BASE_URL", "http://prompt-service:8000")
		self.retrieval_service_base_url = os.getenv("RETRIEVAL_SERVICE_BASE_URL", "http://retrieval-service:8000")
		self.orchestrator_base_url = os.getenv("ORCHESTRATOR_BASE_URL", "http://orchestrator:8000")
		self.agent_service_base_url = os.getenv("AGENT_SERVICE_BASE_URL", "http://agent-service:8000")
		self.use_agent_service = os.getenv("USE_AGENT_SERVICE", "true").lower() == "true"
		self.kafka_bootstrap = os.getenv("KAFKA_BOOTSTRAP", "broker:9092")
		self.topic_tasks = os.getenv("TOPIC_TASKS", "analysis.tasks")
		self.context_segment_limit = int(os.getenv("CONTEXT_SEGMENT_LIMIT", "12"))
		self.qa_top_k = int(os.getenv("QA_TOP_K", "4"))
		self.prompt_cache_ttl_sec = int(os.getenv("PROMPT_CACHE_TTL_SEC", "300"))
		self.provider_hint = os.getenv("MODEL_PROVIDER_HINT", "openai")
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

