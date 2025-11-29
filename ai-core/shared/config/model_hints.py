import os
import json
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass(frozen=True)
class ModelHintsConfig:
	global_default: str
	task_defaults: Dict[str, str]
	service_overrides: Dict[str, Dict[str, str]]

	@staticmethod
	def from_env() -> "ModelHintsConfig":
		global_default = os.getenv("MODEL_HINT_DEFAULT", "ollama")
		
		task_defaults_raw = os.getenv(
			"MODEL_HINT_TASK_DEFAULTS",
			'{"summary":"ollama","qa":"ollama","argument":"ollama","logic_bias":"ollama","sentiment":"ollama","planner":"ollama","answer":"ollama","implication":"ollama","claim":"ollama","reason":"ollama"}'
		)
		try:
			task_defaults: Dict[str, str] = json.loads(task_defaults_raw)
		except Exception:
			task_defaults = {
				"summary": global_default,
				"qa": global_default,
				"argument": global_default,
				"logic_bias": global_default,
				"sentiment": global_default,
				"planner": global_default,
				"answer": global_default,
				"implication": global_default,
				"claim": global_default,
				"reason": global_default,
			}

		service_overrides_raw = os.getenv("MODEL_HINT_SERVICE_OVERRIDES", "{}")
		try:
			service_overrides: Dict[str, Dict[str, str]] = json.loads(service_overrides_raw)
		except Exception:
			service_overrides = {}

		return ModelHintsConfig(
			global_default=global_default,
			task_defaults=task_defaults,
			service_overrides=service_overrides,
		)

	def get_hint(self, task: str, service: Optional[str] = None) -> str:
		if service and service in self.service_overrides:
			service_tasks = self.service_overrides[service]
			if task in service_tasks:
				return service_tasks[task]
		
		return self.task_defaults.get(task, self.global_default)


_config_instance: Optional[ModelHintsConfig] = None


def get_model_hint(task: str, service: Optional[str] = None) -> str:
	global _config_instance
	if _config_instance is None:
		_config_instance = ModelHintsConfig.from_env()
	return _config_instance.get_hint(task, service)


def get_task_hint(task: str) -> str:
	return get_model_hint(task, None)


def get_service_task_hint(task: str, service: str) -> str:
	return get_model_hint(task, service)

