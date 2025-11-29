import os
from dataclasses import dataclass


@dataclass(frozen=True)
class OrchestratorConfig:
	summary_model_hint: str
	sentiment_model_hint: str
	implication_model_hint: str
	argument_claim_model_hint: str
	argument_reason_model_hint: str
	logic_bias_model_hint: str

	@staticmethod
	def from_env() -> "OrchestratorConfig":
		return OrchestratorConfig(
			summary_model_hint=os.getenv("SUMMARY_MODEL_HINT", "ollama"),
			sentiment_model_hint=os.getenv("SENTIMENT_MODEL_HINT", "ollama"),
			implication_model_hint=os.getenv("IMPLICATION_MODEL_HINT", "ollama"),
			argument_claim_model_hint=os.getenv("ARGUMENT_CLAIM_MODEL_HINT", "ollama"),
			argument_reason_model_hint=os.getenv("ARGUMENT_REASON_MODEL_HINT", "ollama"),
			logic_bias_model_hint=os.getenv("LOGIC_BIAS_MODEL_HINT", "ollama"),
		)
