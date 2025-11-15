import os
from dataclasses import dataclass
from typing import Dict, Optional
import json


@dataclass(frozen=True)
class AppConfig:
	provider_keys: Dict[str, str]

	@staticmethod
	def from_env() -> "AppConfig":
		raw = os.getenv("PROVIDER_KEYS", "{}")
		try:
			parsed: Dict[str, str] = json.loads(raw)
		except Exception:
			parsed = {}
		return AppConfig(provider_keys=parsed)

