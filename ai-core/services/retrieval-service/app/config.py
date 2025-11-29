import sys
from pathlib import Path

ai_core_path = Path(__file__).parent.parent.parent.parent
if str(ai_core_path) not in sys.path:
	sys.path.insert(0, str(ai_core_path))

from shared.config.service_configs import RetrievalServiceConfig

_config = RetrievalServiceConfig.from_env()

DATABASE_URL = _config.database_url
MODEL_ADAPTER_BASE_URL = _config.model_adapter_base_url
EMBED_MODEL_HINT = _config.embed_model_hint
EMBEDDING_DIM = _config.embedding_dim
REDIS_URL = _config.redis_url
SEARCH_ALPHA = _config.search_alpha
VEC_CANDIDATES = _config.vec_candidates
TRGM_CANDIDATES = _config.trgm_candidates
TOP_K = _config.top_k

