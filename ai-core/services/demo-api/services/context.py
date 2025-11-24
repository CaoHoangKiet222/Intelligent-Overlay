from domain.schemas import ContextBundle, ContextChunk
from clients.retrieval import RetrievalClient


class ContextPipeline:
	def __init__(self, retrieval_client: RetrievalClient, segment_limit: int = 12):
		self._retrieval = retrieval_client
		self._segment_limit = segment_limit

	async def create_bundle(self, raw_text: str, url: str | None, locale: str | None) -> ContextBundle:
		ingest_result = await self._retrieval.ingest_text(raw_text, url, locale)
		context_id = ingest_result["context_id"]
		segment_dicts = (ingest_result.get("segments") or [])[: self._segment_limit]
		segments = [
			ContextChunk(
				segment_id=seg["segment_id"],
				document_id=seg.get("document_id"),
				text=seg["text"],
				start_offset=seg.get("start_offset"),
				end_offset=seg.get("end_offset"),
				page_no=seg.get("page_no"),
				paragraph_no=seg.get("paragraph_no"),
				sentence_index=seg.get("sentence_index"),
				speaker_label=seg.get("speaker_label"),
				timestamp_start_ms=seg.get("timestamp_start_ms"),
				timestamp_end_ms=seg.get("timestamp_end_ms"),
				metadata=seg.get("metadata") or {},
			)
			for seg in segment_dicts
		]
		return ContextBundle(context_id=context_id, raw_text=raw_text, locale=locale or "auto", source_url=url, segments=segments)

