import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://ai:ai@postgres:5432/ai_core")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
PROMPT_CACHE_TTL_SECONDS = int(os.getenv("PROMPT_CACHE_TTL_SECONDS", "86400"))


