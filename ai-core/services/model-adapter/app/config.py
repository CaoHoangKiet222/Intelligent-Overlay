import os
from dataclasses import dataclass
from typing import Dict, Optional
import json


@dataclass(frozen=True)
class AppConfig:
	provider_keys: Dict[str, str]
	prompt_service_base_url: str
	task_routing: Dict[str, str]

	@staticmethod
	def from_env() -> "AppConfig":
		raw = os.getenv("PROVIDER_KEYS", "{}")
		task_raw = os.getenv("TASK_ROUTING", "{}")
		try:
			parsed: Dict[str, str] = json.loads(raw)
		except Exception:
			parsed = {}
		try:
			task_map: Dict[str, str] = json.loads(task_raw)
		except Exception:
			task_map = {}
		default_map = {
			"summary": "openai",
			"qa": "openai",
			"argument": "anthropic",
			"logic_bias": "anthropic",
		}
		for k, v in default_map.items():
			task_map.setdefault(k, v)
		return AppConfig(
			provider_keys=parsed,
			prompt_service_base_url=os.getenv("PROMPT_SERVICE_BASE_URL", "http://prompt-service:8000"),
			task_routing=task_map,
		)

