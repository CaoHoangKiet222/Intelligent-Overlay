import uuid
from typing import Any, Mapping, Sequence
from fastapi import APIRouter, HTTPException, Query, status
from time import perf_counter
from sqlalchemy import bindparam, text as sql
from pgvector.sqlalchemy import Vector
from domain.schemas import (
	RetrievalMode,
	RetrievalSearchRequest,
	RetrievalSearchResponse,
	RetrievalSpan,
	ContextDetailResponse,
)
from shared.contracts import SpanRef
from domain.scoring import HYBRID_SQL, LEXICAL_SQL, VECTOR_SQL
from domain.highlight import find_local_span
from data.db import SessionLocal
from data.repositories import get_document_by_id, list_segments_by_document, get_embedding_dimension
from clients.model_adapter import embed_texts
from metrics.prometheus import observe_latency, vec_candidates, trgm_candidates
from domain.utils import segment_to_chunk
from domain.vector_utils import expand_vector_to_max_dim, MAX_VECTOR_DIM
from app.config import EMBEDDING_DIM


router = APIRouter(prefix="/retrieval", tags=["retrieval"])
FALLBACK_SEGMENTS_SQL = """
SELECT s.id, s.document_id, s.text, s.start_offset, s.end_offset,
       s.page_no, s.paragraph_no, s.sentence_no
FROM segments s
WHERE s.document_id = :document_id
ORDER BY s.start_offset
LIMIT :limit
"""


def _create_vector_sql_stmt():
	return sql(VECTOR_SQL).bindparams(bindparam("qvec", type_=Vector(MAX_VECTOR_DIM)))


def _create_hybrid_sql_stmt():
	return sql(HYBRID_SQL).bindparams(bindparam("qvec", type_=Vector(MAX_VECTOR_DIM)))


@router.get("/context/{context_id}", response_model=ContextDetailResponse, summary="Fetch context chunks by id")
async def get_context_detail(context_id: str, limit: int = Query(default=12, ge=1, le=100)):
	try:
		context_uuid = uuid.UUID(context_id)
	except ValueError as exc:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_context_id") from exc

	async with SessionLocal() as session:
		document = await get_document_by_id(session, context_uuid)
		if not document:
			raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="context_not_found")
		segments = await list_segments_by_document(session, context_uuid)

	chunks = [segment_to_chunk(seg) for seg in segments[:limit]]
	return ContextDetailResponse(
		context_id=context_id,
		locale=document.locale,
		chunk_count=len(chunks),
		segments=chunks,
	)


@router.post("/search", response_model=RetrievalSearchResponse, summary="Search indexed context chunks")
async def search(payload: RetrievalSearchRequest):
	try:
		context_uuid = uuid.UUID(payload.context_id)
	except ValueError as exc:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_context_id") from exc

	t0 = perf_counter()
	query_vector = None
	query_dim = None
	if payload.mode in (RetrievalMode.VECTOR, RetrievalMode.HYBRID):
		em = await embed_texts([payload.query])
		query_vector = em["vectors"][0]
		query_dim = em.get("dim")
		if query_dim is None and query_vector:
			query_dim = len(query_vector)

	async with SessionLocal() as session:
		document = await get_document_by_id(session, context_uuid)
		if not document:
			raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="context_not_found")

		if payload.mode in (RetrievalMode.VECTOR, RetrievalMode.HYBRID):
			db_dim = await get_embedding_dimension(session, context_uuid)
			if db_dim is not None:
				query_dim = db_dim
			if query_dim is None:
				query_dim = EMBEDDING_DIM
			query_vector = expand_vector_to_max_dim(query_vector, query_dim)

		if payload.mode == RetrievalMode.LEXICAL:
			rows = await _run_lexical(session, context_uuid, payload.query, payload.top_k)
			trgm_candidates.inc(payload.top_k * 4)
		elif payload.mode == RetrievalMode.VECTOR:
			rows = await _run_vector(session, context_uuid, query_vector, query_dim, payload.top_k)
			vec_candidates.inc(payload.top_k)
		else:
			rows = await _run_hybrid(session, context_uuid, payload, query_vector, query_dim)
			vec_candidates.inc(payload.top_k * 4)
			trgm_candidates.inc(payload.top_k * 4)

	took_ms = int((perf_counter() - t0) * 1000)
	observe_latency(took_ms)

	results = [_row_to_span(payload.query, row, payload.mode) for row in rows[: payload.top_k]]

	return RetrievalSearchResponse(
		context_id=payload.context_id,
		query=payload.query,
		mode=payload.mode,
		top_k=payload.top_k,
		took_ms=took_ms,
		results=results,
	)


async def _run_vector(session, context_id: uuid.UUID, query_vector: Sequence[float], dim: int, limit: int):
	stmt = _create_vector_sql_stmt()
	raw_rows = (
		await session.execute(
			stmt,
			{"document_id": context_id, "qvec": list(query_vector), "query_dim": dim, "limit": max(limit * 4, limit)},
		)
	).mappings().all()
	rows = []
	for row in raw_rows:
		data = dict(row)
		data["score"] = float(data["vscore"])
		data["breakdown"] = {"vector": data["score"]}
		rows.append(data)
	return rows


async def _run_lexical(session, context_id: uuid.UUID, query: str, limit: int):
	raw_rows = (
		await session.execute(
			sql(LEXICAL_SQL),
			{"document_id": context_id, "query": query, "limit": max(limit * 4, limit)},
		)
	).mappings().all()
	if not raw_rows:
		raw_rows = (
			await session.execute(sql(FALLBACK_SEGMENTS_SQL), {"document_id": context_id, "limit": limit})
		).mappings().all()
	rows = []
	for row in raw_rows:
		data = dict(row)
		data["score"] = float(data.get("tscore") or 0.0)
		data["breakdown"] = {"lexical": data["score"]}
		rows.append(data)
	return rows


async def _run_hybrid(session, context_id: uuid.UUID, payload: RetrievalSearchRequest, query_vector: Sequence[float], dim: int):
	stmt = _create_hybrid_sql_stmt()
	params = {
		"document_id": context_id,
		"query": payload.query,
		"qvec": list(query_vector),
		"query_dim": dim,
		"alpha": payload.alpha,
		"vec_k": max(payload.top_k * 4, payload.top_k),
		"trgm_k": max(payload.top_k * 4, payload.top_k),
		"top_k": payload.top_k,
	}
	raw_rows = (await session.execute(stmt, params)).mappings().all()
	rows = []
	for row in raw_rows:
		data = dict(row)
		data["score"] = float(data["hybrid"])
		data["breakdown"] = {
			"vector": float(data.get("vscore") or 0.0),
			"lexical": float(data.get("tscore") or 0.0),
		}
		rows.append(data)
	return rows


def _row_to_span(query: str, row: Mapping[str, Any], mode: RetrievalMode) -> RetrievalSpan:
	text = row["text"]
	local = find_local_span(text, query)
	base_start = row.get("start_offset") or 0
	start_offset = row.get("start_offset")
	end_offset = row.get("end_offset")
	if local:
		start_offset = base_start + local["start"]
		end_offset = base_start + local["end"]
	span = SpanRef(
		segment_id=str(row["id"]),
		start_offset=start_offset,
		end_offset=end_offset,
		sentence_index=row.get("sentence_no"),
		text_preview=text[:200],
		score=row["score"],
	)
	return RetrievalSpan(
		span=span,
		snippet=_build_snippet(text, local),
		score=row["score"],
		breakdown=row.get("breakdown") or {mode.value: row["score"]},
	)


def _build_snippet(text: str, local_span: Mapping[str, int] | None):
	if not local_span:
		return text[:320]
	start = max(0, local_span["start"] - 60)
	end = min(len(text), local_span["end"] + 160)
	prefix = "..." if start > 0 else ""
	suffix = "..." if end < len(text) else ""
	return f"{prefix}{text[start:end]}{suffix}"
