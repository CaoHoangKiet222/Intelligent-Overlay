from prometheus_client import Counter, make_asgi_app

prompt_cache_hit = Counter("prompt_cache_hit_total", "Prompt cache hits")
prompt_cache_miss = Counter("prompt_cache_miss_total", "Prompt cache misses")
prompt_cache_invalidate = Counter("prompt_cache_invalidations_total", "Prompt cache invalidations")

metrics_app = make_asgi_app()


