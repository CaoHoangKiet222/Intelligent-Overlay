from fastapi import APIRouter, HTTPException, status
from domain.context_pipeline import IngestionService
from domain.schemas import IngestionRequest, IngestionResponse
from metrics.prometheus import observe_ingestion_latency, record_ingestion_error, record_chunks_created, record_embeddings_computed
from time import perf_counter


router = APIRouter(prefix="/contexts", tags=["contexts"])
_service = IngestionService()


@router.post(
	"/ingest",
	response_model=IngestionResponse,
	summary="Ingest ActivationPayload and persist ContextBundle + ContextChunks with embeddings",
)
async def ingest_context(payload: IngestionRequest):
	t0 = perf_counter()
	try:
		activation_payload = payload.get_activation_payload()
		bundle = await _service.run(activation_payload)
	except ValueError as exc:
		record_ingestion_error("validation_error")
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
	except Exception as exc:
		record_ingestion_error("internal_error")
		raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
	
	took_ms = int((perf_counter() - t0) * 1000)
	observe_ingestion_latency(took_ms)
	record_chunks_created(len(bundle.segments))
	record_embeddings_computed(len(bundle.segments))

	return IngestionResponse(
		context_id=bundle.context_id,
		locale=bundle.locale,
		chunk_count=len(bundle.segments),
		deduplicated=bool(bundle.metadata.get("deduplicated")) if bundle.metadata else False,
		segments=bundle.segments,
	)
