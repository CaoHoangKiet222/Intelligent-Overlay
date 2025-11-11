import asyncio
import ray
from typing import List
from time import perf_counter
from domain.schemas import AnalysisTask, WorkerResult
from workers.summary_worker import run_summary
from workers.argument_worker import run_argument
from workers.sentiment_worker import run_sentiment
from workers.logic_bias_worker import run_logic_bias
from orchestration.aggregator import aggregate
from data.repositories import LlmCallRepo, AnalysisRunRepo, IdempotencyRepo
from metrics.prometheus import observe_task_latency_ms, worker_failures, fanin_partial, dlq_counter
import os

WORKER_TIMEOUT = int(os.getenv("WORKER_TIMEOUT_SEC", "20"))


class OrchestratorService:
	def __init__(self, llm_repo: LlmCallRepo, run_repo: AnalysisRunRepo, idem_repo: IdempotencyRepo, dlq_producer):
		self.llm_repo = llm_repo
		self.run_repo = run_repo
		self.idem_repo = idem_repo
		self.dlq_producer = dlq_producer

	async def handle_message(self, raw: bytes) -> None:
		t0 = perf_counter()
		task = AnalysisTask.model_validate_json(raw.decode("utf-8"))
		if await self.idem_repo.is_processed(task.event_id):
			return

		ray_tasks = [
			run_summary.remote(task.model_dump()),
			run_argument.remote(task.model_dump()),
			run_sentiment.remote(task.model_dump()),
			run_logic_bias.remote(task.model_dump()),
		]
		results: List[WorkerResult] = []
		done, pending = await asyncio.wait([asyncio.create_task(ray.get(t)) for t in ray_tasks], timeout=WORKER_TIMEOUT)
		for d in done:
			try:
				r = d.result()
				llm_id = await self.llm_repo.write_from_adapter(task, r.get("worker", "unknown"), r.get("llm_call", {}))
				results.append(WorkerResult(worker=r.get("worker", "unknown"), ok=True, output=r.get("output"), llm_call_id=llm_id))
			except Exception as e:
				worker_failures.labels(worker="unknown").inc()
				results.append(WorkerResult(worker="unknown", ok=False, error=str(e)))
		for p in pending:
			p.cancel()
			worker_failures.labels(worker="timeout").inc()
			results.append(WorkerResult(worker="timeout", ok=False, error="timeout"))

		agg = aggregate(task.event_id, results)
		await self.run_repo.upsert(task, agg)
		await self.idem_repo.mark_processed(task.event_id)

		took = int((perf_counter() - t0) * 1000)
		observe_task_latency_ms(took)
		if agg.status == "partial":
			fanin_partial.inc()
		if agg.status == "failed":
			dlq_counter.inc()
			await self.dlq_producer.publish(task.event_id, task.model_dump(), reason=str(agg.error_summary))


