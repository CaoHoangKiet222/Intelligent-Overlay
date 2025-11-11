from fastapi import APIRouter
from time import perf_counter
from sqlalchemy import text as sql
from domain.schemas import SearchRequest, SearchResponse, SegmentResult
from domain.scoring import HYBRID_SQL
from domain.highlight import find_local_span
from data.db import SessionLocal
from clients.model_adapter import embed_texts
from metrics.prometheus import observe_latency, vec_candidates, trgm_candidates


router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=SearchResponse)
async def search(payload: SearchRequest):
	t0 = perf_counter()
	em = await embed_texts([payload.query])
	qvec = em["vectors"][0]

	async with SessionLocal() as s:
		params = {
			"query": payload.query,
			"qvec": qvec,
			"alpha": payload.alpha,
			"vec_k": payload.vec_k,
			"trgm_k": payload.trgm_k,
			"top_k": payload.top_k,
		}
		sql_text = HYBRID_SQL
		if payload.filter_document_ids:
			sql_text = sql_text.replace(
				"FROM embeddings e\n  JOIN segments s ON s.id = e.segment_id",
				"FROM embeddings e\n  JOIN segments s ON s.id = e.segment_id AND s.document_id = ANY(:doc_ids)",
			)
			params["doc_ids"] = payload.filter_document_ids

		rows = (await s.execute(sql(sql_text), params)).mappings().all()

	took_ms = int((perf_counter() - t0) * 1000)
	observe_latency(took_ms)
	vec_candidates.inc(payload.vec_k)
	trgm_candidates.inc(payload.trgm_k)

	results = []
	for r in rows:
		local = find_local_span(r["text"], payload.query)
		results.append(
			SegmentResult(
				segment_id=str(r["id"]),
				document_id=str(r["document_id"]),
				text_preview=r["text"][:400],
				start_offset=r["start_offset"],
				end_offset=r["end_offset"],
				page_no=r["page_no"],
				paragraph_no=r["paragraph_no"],
				sentence_no=r["sentence_no"],
				scores={"vscore": float(r["vscore"]), "tscore": float(r["tscore"]), "hybrid": float(r["hybrid"])},
				local_span=local,
			)
		)
	return SearchResponse(took_ms=took_ms, results=results)


