import os
from dataclasses import dataclass
from typing import Dict, Optional
import json


@dataclass(frozen=True)
class AppConfig:
	provider_keys: Dict[str, str]
	prompt_service_base_url: str
	task_routing: Dict[str, str]
	ollama_base_url: str
	ollama_generation_model: str
	ollama_embedding_model: str

	@staticmethod
	def from_env() -> "AppConfig":
		raw = os.getenv("PROVIDER_KEYS", "{}")
		task_raw = os.getenv("TASK_ROUTING", "{}")
		default_task_raw = os.getenv("TASK_ROUTING_DEFAULTS", '{"summary":"ollama","qa":"ollama","argument":"ollama","logic_bias":"ollama","sentiment":"ollama"}')
		try:
			parsed: Dict[str, str] = json.loads(raw)
		except Exception:
			parsed = {}
		try:
			task_map: Dict[str, str] = json.loads(task_raw)
		except Exception:
			task_map = {}
		try:
			default_map: Dict[str, str] = json.loads(default_task_raw)
		except Exception:
			default_map = {
				"summary": "ollama",
				"qa": "ollama",
				"argument": "ollama",
				"logic_bias": "ollama",
				"sentiment": "ollama",
			}
		for k, v in default_map.items():
			task_map.setdefault(k, v)
		return AppConfig(
			provider_keys=parsed,
			prompt_service_base_url=os.getenv("PROMPT_SERVICE_BASE_URL", "http://prompt-service:8000"),
			task_routing=task_map,
			ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://ollama:11434/api"),
			ollama_generation_model=os.getenv("OLLAMA_GENERATION_MODEL", "phi3:mini"),
			ollama_embedding_model=os.getenv("OLLAMA_EMBEDDING_MODEL", "qwen3-embedding:0.6b"),
		)

