from fastapi import APIRouter, HTTPException
from domain.schemas import (
	ArgumentWorkerOutput,
	ArgumentWorkerRequest,
	ImplicationSentimentOutput,
	ImplicationSentimentRequest,
	LogicBiasOutput,
	LogicBiasRequest,
	SummaryWorkerRequest,
	SummaryWorkerOutput,
)
from workers.summary_worker import summarize_context
from workers.argument_worker import analyze_arguments
from workers.sentiment_worker import analyze_implication_sentiment
from workers.logic_bias_worker import analyze_logic_bias


router = APIRouter(prefix="/workers", tags=["workers"])


@router.post("/summary", response_model=SummaryWorkerOutput)
async def run_summary_worker(request: SummaryWorkerRequest) -> SummaryWorkerOutput:
	try:
		payload, _ = await summarize_context(
			context_id=request.context_id,
			language=request.language,
			prompt_ref=request.prompt_ref,
			segments=request.segments,
		)
		return payload
	except ValueError as exc:
		raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/argument", response_model=ArgumentWorkerOutput)
async def run_argument_worker(request: ArgumentWorkerRequest) -> ArgumentWorkerOutput:
	try:
		payload, _ = await analyze_arguments(
			context_id=request.context_id,
			language=request.language,
			segments=request.segments,
			claim_prompt_ref=request.claim_prompt_ref,
			reason_prompt_ref=request.reason_prompt_ref,
		)
		return payload
	except ValueError as exc:
		raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/implication-sentiment", response_model=ImplicationSentimentOutput)
async def run_implication_sentiment_worker(request: ImplicationSentimentRequest) -> ImplicationSentimentOutput:
	try:
		payload, _ = await analyze_implication_sentiment(
			context_id=request.context_id,
			language=request.language,
			segments=request.segments,
			implication_prompt_ref=request.implication_prompt_ref,
			sentiment_prompt_ref=request.sentiment_prompt_ref,
		)
		return payload
	except ValueError as exc:
		raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/logic-bias", response_model=LogicBiasOutput)
async def run_logic_bias_worker(request: LogicBiasRequest) -> LogicBiasOutput:
	try:
		payload, _ = await analyze_logic_bias(
			context_id=request.context_id,
			language=request.language,
			segments=request.segments,
			prompt_ref=request.prompt_ref,
		)
		return payload
	except ValueError as exc:
		raise HTTPException(status_code=400, detail=str(exc)) from exc

