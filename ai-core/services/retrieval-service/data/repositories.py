from typing import Any, Dict, List, Optional
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from .models import Document, Segment, Embedding, SourceType


async def create_document(s: AsyncSession, payload: Dict[str, Any]) -> Document:
	source_type = payload.get("source_type")
	if isinstance(source_type, str):
		try:
			payload["source_type"] = SourceType(source_type.lower())
		except ValueError:
			payload["source_type"] = SourceType.TEXT
	doc = Document(**payload)
	s.add(doc)
	await s.flush()
	return doc


async def bulk_insert_segments(s: AsyncSession, document_id, items: List[Dict[str, Any]]) -> List[Segment]:
	segs: List[Segment] = [Segment(document_id=document_id, **i) for i in items]
	s.add_all(segs)
	await s.flush()
	return segs


async def bulk_insert_embeddings(s: AsyncSession, pairs: List[Dict[str, Any]]) -> None:
	await s.execute(insert(Embedding), pairs)


async def list_segments_by_document(s: AsyncSession, document_id) -> List[Segment]:
	stmt = select(Segment).where(Segment.document_id == document_id).order_by(Segment.start_offset)
	res = await s.execute(stmt)
	return list(res.scalars().all())


async def get_document_by_hash(s: AsyncSession, content_hash: str) -> Optional[Document]:
	stmt = select(Document).where(Document.content_hash == content_hash)
	res = await s.execute(stmt)
	return res.scalars().first()


async def get_document_by_id(s: AsyncSession, document_id) -> Optional[Document]:
	stmt = select(Document).where(Document.id == document_id)
	res = await s.execute(stmt)
	return res.scalars().first()


async def get_embedding_dimension(s: AsyncSession, document_id) -> Optional[int]:
	stmt = select(Embedding.dim).where(Embedding.segment_id.in_(
		select(Segment.id).where(Segment.document_id == document_id)
	)).limit(1)
	res = await s.execute(stmt)
	dim = res.scalar_one_or_none()
	return dim


