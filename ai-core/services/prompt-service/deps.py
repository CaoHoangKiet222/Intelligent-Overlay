import os
from cache.redis_cache import PromptCache
from data.repositories import PromptRepo
from config import REDIS_URL

_cache = PromptCache(REDIS_URL)
_repo = PromptRepo()

def get_cache_dep() -> PromptCache:
	return _cache

def get_repo_dep() -> PromptRepo:
	return _repo


