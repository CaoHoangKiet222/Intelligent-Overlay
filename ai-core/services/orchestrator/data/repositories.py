from typing import Optional
from .db import SessionLocal
from .models import LlmCall, AnalysisRun, ProcessedEvent


class LlmCallRepo:
	async def write_from_adapter(self, task, worker: str, adapter_resp: dict) -> str:
		async with SessionLocal() as s:
			obj = LlmCall(
				provider=adapter_resp.get("provider", ""),
				model=adapter_resp.get("model", ""),
				session_id=None,
				message_id=None,
				prompt_version_id=None,
				input={"worker": worker, "event_id": task.event_id},
				output=adapter_resp,
				input_tokens=adapter_resp.get("input_tokens"),
				output_tokens=adapter_resp.get("output_tokens"),
				cost_usd=(adapter_resp.get("meta") or {}).get("cost_usd") if isinstance(adapter_resp.get("meta"), dict) else None,
				latency_ms=adapter_resp.get("latency_ms"),
				status=adapter_resp.get("status", "success"),
			)
			s.add(obj)
			await s.commit()
			await s.refresh(obj)
			return str(obj.id)


class AnalysisRunRepo:
	async def upsert(self, task, agg) -> None:
		async with SessionLocal() as s:
			citations = None
			if agg.citations:
				citations = [span.model_dump(by_alias=True) for span in agg.citations]
			obj = AnalysisRun(
				event_id=task.event_id,
				bundle_id=task.bundle_id,
				callback_url=(task.meta or {}).get("callback_url") if isinstance(task.meta, dict) else None,
				status=agg.status,
				summary_json=agg.summary_json,
				argument_json=agg.argument_json,
				sentiment_json=agg.sentiment_json,
				logic_bias_json=agg.logic_bias_json,
				citations=citations,
				error_summary=agg.error_summary,
			)
			s.add(obj)
			await s.commit()

	async def get(self, event_id: str):
		async with SessionLocal() as s:
			return await s.get(AnalysisRun, event_id)


class IdempotencyRepo:
	async def is_processed(self, event_id: str) -> bool:
		async with SessionLocal() as s:
			row = await s.get(ProcessedEvent, event_id)
			return row is not None

	async def mark_processed(self, event_id: str) -> None:
		async with SessionLocal() as s:
			s.add(ProcessedEvent(event_id=event_id))
			await s.commit()


