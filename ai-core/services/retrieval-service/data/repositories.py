from typing import List, Dict, Any
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession
from .models import Document, Segment, Embedding


async def create_document(s: AsyncSession, payload: Dict[str, Any]) -> Document:
	doc = Document(**payload)
	s.add(doc)
	await s.commit()
	await s.refresh(doc)
	return doc


async def bulk_insert_segments(s: AsyncSession, document_id, items: List[Dict[str, Any]]) -> List[Segment]:
	segs: List[Segment] = [Segment(document_id=document_id, **i) for i in items]
	s.add_all(segs)
	await s.commit()
	for sg in segs:
		await s.refresh(sg)
	return segs


async def bulk_insert_embeddings(s: AsyncSession, pairs: List[Dict[str, Any]]) -> None:
	await s.execute(insert(Embedding), pairs)
	await s.commit()


