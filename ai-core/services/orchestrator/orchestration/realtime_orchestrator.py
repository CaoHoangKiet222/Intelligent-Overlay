from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Any, Awaitable, Dict, List, Sequence, Tuple

from domain.schemas import (
	AnalysisBundleResponse,
	ArgumentWorkerOutput,
	ImplicationSentimentOutput,
	LogicBiasOutput,
	SummaryWorkerOutput,
)

WorkerResultPayload = Tuple[Any, Dict[str, object]]


@dataclass
class WorkerCall:
	name: str
	coroutine: Awaitable[WorkerResultPayload]


class RealtimeOrchestrator:
	def __init__(self, *, worker_timeout: float = 15.0):
		self.worker_timeout = worker_timeout
		self.logger = logging.getLogger(__name__)

	async def analyze(
		self,
		worker_calls: Sequence[WorkerCall],
		request_id: str,
	) -> AnalysisBundleResponse:
		results, statuses = await self._run_workers(worker_calls, request_id)
		summary = self._extract_summary(results.get("summary"))
		arguments = self._extract_arguments(results.get("argument"))
		implication_output = self._extract_implication(results.get("implication_sentiment"))
		logic_bias = self._extract_logic_bias(results.get("logic_bias"))

		return AnalysisBundleResponse(
			summary=summary,
			arguments=arguments,
			implications=implication_output.implications if implication_output else [],
			sentiment=implication_output.sentiment if implication_output else None,
			logic_bias=logic_bias,
			worker_statuses=statuses,
		)

	async def _run_workers(
		self,
		worker_calls: Sequence[WorkerCall],
		request_id: str,
	) -> Tuple[Dict[str, WorkerResultPayload], Dict[str, str]]:
		tasks: Dict[asyncio.Task[WorkerResultPayload], str] = {}
		statuses: Dict[str, str] = {}
		results: Dict[str, WorkerResultPayload] = {}

		for call in worker_calls:
			self.logger.info("worker_start", extra={"worker": call.name, "request_id": request_id})
			tasks[asyncio.create_task(call.coroutine)] = call.name

		done, pending = await asyncio.wait(tasks.keys(), timeout=self.worker_timeout)

		for task in done:
			worker_name = tasks[task]
			try:
				result = task.result()
				results[worker_name] = result
				statuses[worker_name] = "ok"
				self.logger.info("worker_ok", extra={"worker": worker_name, "request_id": request_id})
			except Exception as exc:
				statuses[worker_name] = "error"
				self.logger.exception(
					"worker_error",
					exc_info=exc,
					extra={"worker": worker_name, "request_id": request_id},
				)

		for task in pending:
			worker_name = tasks[task]
			task.cancel()
			statuses[worker_name] = "timeout"
			self.logger.warning("worker_timeout", extra={"worker": worker_name, "request_id": request_id})

		if pending:
			await asyncio.gather(*pending, return_exceptions=True)

		return results, statuses

	def _extract_summary(self, result: WorkerResultPayload | None) -> SummaryWorkerOutput | None:
		if not result:
			return None
		payload, _ = result
		if isinstance(payload, SummaryWorkerOutput):
			return payload
		return None

	def _extract_arguments(self, result: WorkerResultPayload | None) -> ArgumentWorkerOutput | None:
		if not result:
			return None
		payload, _ = result
		if isinstance(payload, ArgumentWorkerOutput):
			return payload
		return None

	def _extract_implication(
		self,
		result: WorkerResultPayload | None,
	) -> ImplicationSentimentOutput | None:
		if not result:
			return None
		payload, _ = result
		if isinstance(payload, ImplicationSentimentOutput):
			return payload
		if isinstance(payload, dict):
			try:
				return ImplicationSentimentOutput.model_validate(payload)
			except Exception:
				return None
		return None

	def _extract_logic_bias(self, result: WorkerResultPayload | None) -> LogicBiasOutput | None:
		if not result:
			return None
		payload, _ = result
		if isinstance(payload, LogicBiasOutput):
			return payload
		return None


REALTIME_WORKER_TIMEOUT = float(os.getenv("REALTIME_WORKER_TIMEOUT", "15"))
REALTIME_ORCHESTRATOR = RealtimeOrchestrator(worker_timeout=REALTIME_WORKER_TIMEOUT)

