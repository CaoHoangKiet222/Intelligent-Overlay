from prometheus_client import Summary, Counter, make_asgi_app

latency = Summary("agent_ask_latency_ms", "End-to-end /agent/ask latency (ms)")
fallback_used = Counter("agent_fallback_total", "Fallback used count")
tool_errors = Counter("agent_tool_errors_total", "Tool call error count")

metrics_app = make_asgi_app()


