from prometheus_client import Summary, Counter, make_asgi_app

_query_latency = Summary("retrieval_query_latency_ms", "Hybrid search latency (ms)")
vec_candidates = Counter("retrieval_vec_candidates", "Vector candidate requests")
trgm_candidates = Counter("retrieval_trgm_candidates", "Trigram candidate requests")


def observe_latency(ms: int):
	_query_latency.observe(ms)


metrics_app = make_asgi_app()


