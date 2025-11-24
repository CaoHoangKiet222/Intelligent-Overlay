from __future__ import annotations

import os
import uuid
from typing import Dict

from fastapi import APIRouter, HTTPException, Request

from domain.schemas import (
	AnalysisBundleResponse,
	OrchestratorAnalyzeRequest,
)
from orchestration.realtime_orchestrator import REALTIME_ORCHESTRATOR, WorkerCall
from workers.argument_worker import analyze_arguments
from workers.logic_bias_worker import analyze_logic_bias
from workers.sentiment_worker import analyze_implication_sentiment
from workers.summary_worker import summarize_context
from workers.utils import fetch_context_chunks, normalize_chunks

router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])
ANALYSIS_SEGMENT_LIMIT = int(os.getenv("ANALYSIS_SEGMENT_LIMIT", "12"))


@router.post("/analyze", response_model=AnalysisBundleResponse)
async def orchestrator_analyze(
	payload: OrchestratorAnalyzeRequest,
	request: Request,
) -> AnalysisBundleResponse:
	if not payload.context_id:
		raise HTTPException(status_code=400, detail="context_id_required")
	segments = normalize_chunks(payload.segments)
	if not segments:
		try:
			segments = await fetch_context_chunks(payload.context_id, ANALYSIS_SEGMENT_LIMIT)
		except Exception as exc:
			raise HTTPException(status_code=502, detail=f"context_fetch_failed:{exc}") from exc
	if not segments:
		raise HTTPException(status_code=404, detail="context_not_found")

	prompt_ids = payload.prompt_ids or {}
	language = payload.language or "auto"
	request_id = request.headers.get("x-request-id") or str(uuid.uuid4())

	worker_calls = _build_worker_calls(
		context_id=payload.context_id,
		segments=segments,
		language=language,
		prompt_ids=prompt_ids,
	)

	return await REALTIME_ORCHESTRATOR.analyze(worker_calls, request_id=request_id)


def _build_worker_calls(
	context_id: str,
	segments,
	language: str,
	prompt_ids: Dict[str, str],
) -> list[WorkerCall]:
	return [
		WorkerCall(
			name="summary",
			coroutine=summarize_context(
				context_id=context_id,
				language=language,
				prompt_ref=prompt_ids.get("summary"),
				segments=segments,
			),
		),
		WorkerCall(
			name="argument",
			coroutine=analyze_arguments(
				context_id=context_id,
				language=language,
				segments=segments,
				claim_prompt_ref=prompt_ids.get("argument_claim"),
				reason_prompt_ref=prompt_ids.get("argument_reason"),
			),
		),
		WorkerCall(
			name="implication_sentiment",
			coroutine=analyze_implication_sentiment(
				context_id=context_id,
				language=language,
				segments=segments,
				implication_prompt_ref=prompt_ids.get("implication"),
				sentiment_prompt_ref=prompt_ids.get("sentiment"),
			),
		),
		WorkerCall(
			name="logic_bias",
			coroutine=analyze_logic_bias(
				context_id=context_id,
				language=language,
				segments=segments,
				prompt_ref=prompt_ids.get("logic_bias"),
			),
		),
	]

