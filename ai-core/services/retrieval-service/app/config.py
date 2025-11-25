import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://ai:ai@postgres:5432/ai_core")
MODEL_ADAPTER_BASE_URL = os.getenv("MODEL_ADAPTER_BASE_URL", "http://model-adapter:8000")
EMBED_MODEL_HINT = os.getenv("EMBED_MODEL_HINT", "text-embedding-3-small")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "1536"))
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
SEARCH_ALPHA = float(os.getenv("SEARCH_ALPHA", "0.7"))
VEC_CANDIDATES = int(os.getenv("VEC_CANDIDATES", "100"))
TRGM_CANDIDATES = int(os.getenv("TRGM_CANDIDATES", "200"))
TOP_K = int(os.getenv("TOP_K", "10"))

