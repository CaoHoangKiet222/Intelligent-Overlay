import time
from functools import wraps
from .metrics import http_requests_total, http_request_duration_ms, llm_tokens_total, llm_cost_usd_total, llm_latency_ms
from .cost_table import estimate_cost


def http_metrics(route_name: str, method: str = "POST"):
	def deco(fn):
		@wraps(fn)
		async def _inner(*args, **kwargs):
			start = time.perf_counter()
			code = "200"
			try:
				res = await fn(*args, **kwargs)
				code = str(getattr(res, "status_code", 200))
				return res
			except Exception:
				code = "500"
				raise
			finally:
				dur = (time.perf_counter() - start) * 1000
				http_requests_total.labels(route=route_name, method=method, code=code).inc()
				http_request_duration_ms.labels(route=route_name, method=method).observe(dur)
		return _inner
	return deco


def llm_usage(provider: str, model: str, tokens_in: int | None, tokens_out: int | None, latency_ms: int | None) -> float:
	llm_tokens_total.labels(provider=provider, model=model, type="in").inc(tokens_in or 0)
	llm_tokens_total.labels(provider=provider, model=model, type="out").inc(tokens_out or 0)
	llm_latency_ms.labels(provider=provider, model=model).observe(latency_ms or 0)
	cost = estimate_cost(provider, model, tokens_in, tokens_out)
	llm_cost_usd_total.labels(provider=provider, model=model).inc(cost or 0.0)
	return cost


