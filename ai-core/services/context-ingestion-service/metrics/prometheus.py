from prometheus_client import Summary, Counter, make_asgi_app

_ingestion_latency = Summary("context_ingestion_latency_ms", "Context ingestion latency (ms)")
_ingestion_errors = Counter("context_ingestion_errors", "Context ingestion errors", ["error_type"])
_chunks_created = Counter("context_chunks_created", "Total context chunks created")
_embeddings_computed = Counter("context_embeddings_computed", "Total embeddings computed")


def observe_ingestion_latency(ms: int):
	_ingestion_latency.observe(ms)


def record_ingestion_error(error_type: str):
	_ingestion_errors.labels(error_type=error_type).inc()


def record_chunks_created(count: int):
	_chunks_created.inc(count)


def record_embeddings_computed(count: int):
	_embeddings_computed.inc(count)


metrics_app = make_asgi_app()

