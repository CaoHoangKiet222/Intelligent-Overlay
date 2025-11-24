from fastapi import APIRouter, HTTPException, status
from domain.context_pipeline import NormalizeAndIndexService
from domain.schemas import NormalizeAndIndexRequest, NormalizeAndIndexResponse


router = APIRouter(prefix="/ingestion", tags=["ingestion"])
_service = NormalizeAndIndexService()


@router.post(
	"/normalize_and_index",
	response_model=NormalizeAndIndexResponse,
	summary="Normalize raw text and index context chunks",
)
async def normalize_and_index(payload: NormalizeAndIndexRequest):
	try:
		bundle = await _service.run(payload.raw_text, payload.url, payload.locale)
	except ValueError as exc:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

	return NormalizeAndIndexResponse(
		context_id=bundle.context_id,
		locale=bundle.locale,
		chunk_count=len(bundle.segments),
		deduplicated=bool(bundle.metadata.get("deduplicated")) if bundle.metadata else False,
		segments=bundle.segments,
	)


