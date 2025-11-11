from prometheus_client import Counter, Summary, make_asgi_app

worker_failures = Counter("orchestrator_worker_failures_total", "Worker failures", ["worker"])
fanin_partial = Counter("orchestrator_fanin_partial_total", "Partial fan-in results")
dlq_counter = Counter("orchestrator_dlq_total", "DLQ publish count")
_task_latency = Summary("orchestrator_task_latency_ms", "End-to-end task latency (ms)")


def observe_task_latency_ms(ms: int):
	_task_latency.observe(ms)


metrics_app = make_asgi_app()


