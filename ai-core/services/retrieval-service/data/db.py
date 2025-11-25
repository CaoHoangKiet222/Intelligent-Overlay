import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.config import DATABASE_URL


engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
	pass


async def ensure_extensions() -> None:
	async with engine.begin() as conn:
		for extension in ("vector", "pg_trgm"):
			try:
				await conn.execute(text(f"CREATE EXTENSION IF NOT EXISTS {extension}"))
			except Exception as exc:  # pragma: no cover - only logs
				logging.getLogger(__name__).warning("Failed to ensure extension %s: %s", extension, exc)


