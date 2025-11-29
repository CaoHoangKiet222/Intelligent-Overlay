import os


class AgentConfig:
	planner_model_hint: str
	answer_model_hint: str

	@staticmethod
	def from_env() -> "AgentConfig":
		return AgentConfig(
			planner_model_hint=os.getenv("AGENT_PLANNER_MODEL_HINT", "ollama"),
			answer_model_hint=os.getenv("AGENT_ANSWER_MODEL_HINT", "ollama"),
		)

