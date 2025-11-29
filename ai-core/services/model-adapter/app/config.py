import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Dict

ai_core_path = Path(__file__).parent.parent.parent.parent
if str(ai_core_path) not in sys.path:
	sys.path.insert(0, str(ai_core_path))

from shared.config.model_hints import get_task_hint
from shared.config.service_configs import ModelAdapterConfig


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
		import os
		import json
		
		service_config = ModelAdapterConfig.from_env()
		
		default_tasks = ["summary", "qa", "argument", "logic_bias", "sentiment"]
		task_map = service_config.task_routing.copy()
		for task in default_tasks:
			if task not in task_map:
				task_map[task] = get_task_hint(task)
		
		return AppConfig(
			provider_keys=service_config.provider_keys,
			prompt_service_base_url=service_config.prompt_service_base_url,
			task_routing=task_map,
			ollama_base_url=service_config.ollama_base_url,
			ollama_generation_model=service_config.ollama_generation_model,
			ollama_embedding_model=service_config.ollama_embedding_model,
		)

