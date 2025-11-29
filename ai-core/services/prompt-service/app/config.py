import sys
from pathlib import Path
import os

ai_core_path = Path(__file__).parent.parent.parent.parent
if str(ai_core_path) not in sys.path:
	sys.path.insert(0, str(ai_core_path))

from shared.config.service_configs import PromptServiceConfig
from shared.config.base import get_base_config

_service_config = PromptServiceConfig.from_env()
_base_config = get_base_config()

DATABASE_URL = _base_config.database_url
DB_DSN = _service_config.database_dsn
REDIS_URL = _base_config.redis_url
PROMPT_CACHE_TTL_SECONDS = int(os.getenv("PROMPT_CACHE_TTL_SECONDS", "86400"))

