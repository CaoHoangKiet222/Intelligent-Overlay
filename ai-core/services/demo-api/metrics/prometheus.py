from prometheus_client import Summary, Counter, make_asgi_app


analyze_latency = Summary("demo_analyze_latency_ms", "Latency for /demo/analyze (ms)")
qa_latency = Summary("demo_qa_latency_ms", "Latency for /demo/qa (ms)")
worker_counter = Counter("demo_worker_invocations_total", "Worker invocation count", ["worker"])

metrics_app = make_asgi_app()

