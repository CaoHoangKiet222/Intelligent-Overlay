from prometheus_client import Counter, Histogram, Gauge, make_asgi_app

# HTTP
http_requests_total = Counter("http_requests_total", "HTTP requests", ["route", "method", "code"])
http_request_duration_ms = Histogram("http_request_duration_ms", "HTTP latency (ms)", ["route", "method"])

# LLM
llm_tokens_total = Counter("llm_tokens_total", "LLM tokens", ["provider", "model", "type"])  # type=in|out
llm_cost_usd_total = Counter("llm_cost_usd_total", "LLM cost in USD", ["provider", "model"])
llm_latency_ms = Histogram("llm_latency_ms", "LLM call latency (ms)", ["provider", "model"])

# Kafka
kafka_consumer_lag = Gauge("kafka_consumer_lag", "Consumer lag per partition", ["topic", "partition", "group"])

# App errors
app_errors_total = Counter("app_errors_total", "Application errors", ["type"])

metrics_app = make_asgi_app()


