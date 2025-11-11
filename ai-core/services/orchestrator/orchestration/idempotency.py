from data.db import SessionLocal
from sqlalchemy import select
from data.models import ProcessedEvent


async def is_processed(event_id: str) -> bool:
	async with SessionLocal() as s:
		row = await s.get(ProcessedEvent, event_id)
		return row is not None


async def mark_processed(event_id: str) -> None:
	async with SessionLocal() as s:
		s.add(ProcessedEvent(event_id=event_id))
		await s.commit()


