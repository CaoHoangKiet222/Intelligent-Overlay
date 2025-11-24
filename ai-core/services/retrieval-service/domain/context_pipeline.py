import hashlib
import re
from typing import Iterable, List, Sequence, Tuple
from shared.contracts import ContextBundle, ContextChunk
from clients.model_adapter import embed_texts
from data.db import SessionLocal
from data.models import Segment
from data.repositories import (
	create_document,
	bulk_insert_embeddings,
	bulk_insert_segments,
	get_document_by_hash,
	list_segments_by_document,
)
from domain.segmentation import segment_text


def normalize_text(raw: str) -> str:
	text = raw.replace("\r\n", "\n").strip()
	text = re.sub(r"\u00A0", " ", text)
	text = re.sub(r"[ \t]+", " ", text)
	text = re.sub(r"\n{3,}", "\n\n", text)
	return text.strip()


def segment_to_chunk(segment: Segment) -> ContextChunk:
	return ContextChunk(
		segment_id=str(segment.id),
		document_id=str(segment.document_id),
		text=segment.text,
		start_offset=segment.start_offset,
		end_offset=segment.end_offset,
		page_no=segment.page_no,
		paragraph_no=segment.paragraph_no,
		sentence_index=segment.sentence_no,
		speaker_label=segment.speaker_label,
		timestamp_start_ms=segment.timestamp_start_ms,
		timestamp_end_ms=segment.timestamp_end_ms,
		metadata={"position": segment.sentence_no},
	)


class NormalizeAndIndexService:
	def __init__(self, max_chars: int = 900, overlap: int = 120, embed_batch: int = 32):
		self._max_chars = max_chars
		self._overlap = overlap
		self._embed_batch = max(1, embed_batch)

	async def run(self, raw_text: str, url: str | None, locale: str | None) -> ContextBundle:
		normalized = normalize_text(raw_text)
		if not normalized:
			raise ValueError("normalized_text_empty")
		content_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()

		async with SessionLocal() as session:
			existing = await get_document_by_hash(session, content_hash)
			if existing:
				segments = await list_segments_by_document(session, existing.id)
				return ContextBundle(
					context_id=str(existing.id),
					raw_text=normalized,
					locale=existing.locale or locale or "auto",
					source_url=url,
					segments=[segment_to_chunk(seg) for seg in segments],
					metadata={"deduplicated": True},
				)

		segments_data = segment_text(normalized, max_chars=self._max_chars, overlap=self._overlap)
		if not segments_data:
			raise ValueError("no_segments_generated")

		vectors, model, dim = await self._embed_chunks([item["text"] for item in segments_data])

		async with SessionLocal() as session:
			async with session.begin():
				doc = await create_document(
					session,
					{
						"source_type": "text",
						"source_url": url,
						"title": None,
						"locale": locale or "auto",
						"content_hash": content_hash,
						"meta": {"chunk_count": len(segments_data)},
					},
				)
				segments_payload = [
					{
						"text": item["text"],
						"start_offset": item.get("start_offset"),
						"end_offset": item.get("end_offset"),
						"sentence_no": idx,
					}
					for idx, item in enumerate(segments_data)
				]
				segment_records = await bulk_insert_segments(session, doc.id, segments_payload)
				embedding_rows = [
					{"segment_id": seg.id, "model": model, "dim": dim, "vector": vec}
					for seg, vec in zip(segment_records, vectors)
				]
				if embedding_rows:
					await bulk_insert_embeddings(session, embedding_rows)
			return ContextBundle(
				context_id=str(doc.id),
				raw_text=normalized,
				locale=locale or "auto",
				source_url=url,
				segments=[segment_to_chunk(seg) for seg in segment_records],
			)

	async def _embed_chunks(self, texts: Sequence[str]) -> Tuple[List[List[float]], str, int]:
		vectors: List[List[float]] = []
		model_name: str | None = None
		dimension: int | None = None
		for batch in _batched(texts, self._embed_batch):
			if not batch:
				continue
			resp = await embed_texts(list(batch))
			batch_vectors = resp.get("vectors") or []
			if not batch_vectors:
				raise ValueError("embedding_vectors_missing")
			vectors.extend(batch_vectors)
			model_name = resp.get("model", model_name)
			dimension = resp.get("dim", dimension)
		if len(vectors) != len(texts):
			raise ValueError("embedding_count_mismatch")
		if model_name is None or dimension is None:
			raise ValueError("embedding_metadata_missing")
		return vectors, model_name, dimension


def _batched(items: Sequence[str], size: int) -> Iterable[Sequence[str]]:
	for idx in range(0, len(items), size):
		yield items[idx: idx + size]

