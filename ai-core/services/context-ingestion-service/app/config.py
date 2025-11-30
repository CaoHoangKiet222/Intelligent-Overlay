import sys
from pathlib import Path

ai_core_path = Path(__file__).parent.parent.parent.parent
if str(ai_core_path) not in sys.path:
	sys.path.insert(0, str(ai_core_path))

from shared.config.service_configs import ContextIngestionServiceConfig

_config = ContextIngestionServiceConfig.from_env()

DATABASE_URL = _config.database_url
MODEL_ADAPTER_BASE_URL = _config.model_adapter_base_url
EMBED_MODEL_HINT = _config.embed_model_hint
EMBEDDING_DIM = _config.embedding_dim

