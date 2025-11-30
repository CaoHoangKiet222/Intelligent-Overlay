import hashlib
import re
from typing import Iterable, List, Sequence, Tuple
from shared.contracts import ContextBundle, ContextChunk
from clients.model_adapter import embed_texts
from services.vision_ocr import extract_text_from_image
from services.stt import transcribe_audio
from data.db import SessionLocal
from data.models import Segment, SourceType
from data.repositories import (
	create_document,
	bulk_insert_embeddings,
	bulk_insert_segments,
	get_document_by_hash,
	list_segments_by_document,
)
from app.config import EMBEDDING_DIM
from domain.segmentation import segment_text
from domain.schemas import ActivationPayload, ActivationSourceType
from domain.vector import expand_vector_to_max_dim


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


class IngestionService:
	def __init__(
		self,
		max_chars: int = 900,
		overlap: int = 120,
		embed_batch: int = 32
	):
		self._max_chars = max_chars
		self._overlap = overlap
		self._embed_batch = max(1, embed_batch)

	async def run(self, payload: ActivationPayload) -> ContextBundle:
		raw_text = await self._extract_text_from_payload(payload)
		url = payload.url
		locale = payload.locale or "auto"
		source_type = self._map_source_type(payload.source_type)
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
					source_type=source_type.value,
					segments=[segment_to_chunk(seg) for seg in segments],
					metadata={"deduplicated": True, "app_id": payload.app_id},
				)

		if payload.transcript_segments:
			segments_data = self._segment_from_transcript(payload.transcript_segments, normalized)
		else:
			segments_data = segment_text(normalized, max_chars=self._max_chars, overlap=self._overlap)

		if not segments_data:
			raise ValueError("no_segments_generated")

		vectors, model, dim = await self._embed_chunks([item["text"] for item in segments_data])

		async with SessionLocal() as session:
			async with session.begin():
				meta = {
					"chunk_count": len(segments_data),
					"app_id": payload.app_id,
				}
				if payload.image_metadata:
					meta["image_metadata"] = payload.image_metadata.model_dump()
				
				doc = await create_document(
					session,
					{
						"source_type": source_type.value,
						"source_url": url,
						"title": None,
						"locale": locale or "auto",
						"content_hash": content_hash,
						"meta": meta,
					},
				)
				segments_payload = [
					{
						"text": item["text"],
						"start_offset": item.get("start_offset"),
						"end_offset": item.get("end_offset"),
						"sentence_no": idx,
						"timestamp_start_ms": item.get("timestamp_start_ms"),
						"timestamp_end_ms": item.get("timestamp_end_ms"),
						"speaker_label": item.get("speaker_label"),
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
				source_type=source_type.value,
				segments=[segment_to_chunk(seg) for seg in segment_records],
				metadata={"app_id": payload.app_id},
			)

	async def _extract_text_from_payload(self, payload: ActivationPayload) -> str:
		if payload.raw_text:
			return payload.raw_text

		if payload.source_type == ActivationSourceType.IMAGE:
			if not payload.image_data:
				raise ValueError("image source requires image_data when raw_text is not provided")
			ocr_text = await extract_text_from_image(
				payload.image_data,
				lang_hint=payload.locale
			)
			return ocr_text

		if payload.source_type == ActivationSourceType.VIDEO:
			if payload.transcript_segments:
				return "\n".join(seg.text for seg in payload.transcript_segments)
			if not payload.audio_data:
				raise ValueError("video source requires audio_data or transcript_segments when raw_text is not provided")
			segments = await transcribe_audio(
				payload.audio_data,
				lang_hint=payload.locale
			)
			return "\n".join(seg.text for seg in segments)

		raise ValueError(f"{payload.source_type} source requires raw_text")

	def _map_source_type(self, source_type: ActivationSourceType) -> SourceType:
		mapping = {
			ActivationSourceType.BROWSER: SourceType.BROWSER,
			ActivationSourceType.SHARE: SourceType.SHARE,
			ActivationSourceType.SELECTION: SourceType.SELECTION,
			ActivationSourceType.BUBBLE: SourceType.BUBBLE,
			ActivationSourceType.BACKTAP: SourceType.BACKTAP,
			ActivationSourceType.NOTI: SourceType.NOTI,
			ActivationSourceType.IMAGE: SourceType.IMAGE,
			ActivationSourceType.VIDEO: SourceType.VIDEO,
		}
		return mapping.get(source_type, SourceType.TEXT)

	def _segment_from_transcript(
		self,
		transcript_segments: List,
		normalized_text: str
	) -> List[dict]:
		segments = []
		current_offset = 0
		for seg in transcript_segments:
			text = seg.text if hasattr(seg, "text") else seg.get("text", "")
			if not text:
				continue
			start_offset = current_offset
			end_offset = current_offset + len(text)
			segments.append({
				"text": text,
				"start_offset": start_offset,
				"end_offset": end_offset,
				"timestamp_start_ms": seg.start_ms if hasattr(seg, "start_ms") else seg.get("start_ms"),
				"timestamp_end_ms": seg.end_ms if hasattr(seg, "end_ms") else seg.get("end_ms"),
				"speaker_label": seg.speaker_label if hasattr(seg, "speaker_label") else seg.get("speaker_label"),
			})
			current_offset = end_offset + 1
		return segments

	async def _embed_chunks(self, texts: Sequence[str]) -> Tuple[List[List[float]], str, int]:
		vectors: List[List[float]] = []
		model_name: str | None = None
		dimension: int | None = None
		for batch in _batched(texts, self._embed_batch):
			if not batch:
				continue
			resp = await embed_texts(list(batch))
			batch_vectors_raw = resp.get("vectors") or []
			response_dim = resp.get("dim")
			if response_dim is not None:
				dimension = response_dim
			if dimension is None:
				if batch_vectors_raw:
					dimension = len(batch_vectors_raw[0])
			if dimension is None:
				dimension = EMBEDDING_DIM
			batch_vectors = [expand_vector_to_max_dim(vec, dimension) for vec in batch_vectors_raw]
			if not batch_vectors:
				raise ValueError("embedding_vectors_missing")
			vectors.extend(batch_vectors)
			model_name = resp.get("model", model_name)
		if len(vectors) != len(texts):
			raise ValueError("embedding_count_mismatch")
		if model_name is None or dimension is None:
			raise ValueError("embedding_metadata_missing")
		return vectors, model_name, dimension



def _batched(items: Sequence[str], size: int) -> Iterable[Sequence[str]]:
	for idx in range(0, len(items), size):
		yield items[idx: idx + size]

