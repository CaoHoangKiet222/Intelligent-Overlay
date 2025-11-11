from typing import Optional
from sqlalchemy import select, func
from .db import SessionLocal
from .models import Prompt, PromptVersion
from domain.schemas import PromptCreate, PromptVersionCreate


class PromptRepo:
	async def create_prompt(self, payload: PromptCreate) -> Prompt:
		async with SessionLocal() as s:
			p = Prompt(**payload.model_dump())
			s.add(p)
			await s.commit()
			await s.refresh(p)
			return p

	async def get_prompt_by_key(self, key: str) -> Optional[Prompt]:
		async with SessionLocal() as s:
			res = await s.execute(select(Prompt).where(Prompt.key == key))
			return res.scalar_one_or_none()

	async def get_prompt_by_id(self, prompt_id: str) -> Optional[Prompt]:
		async with SessionLocal() as s:
			res = await s.execute(select(Prompt).where(Prompt.id == prompt_id))
			return res.scalar_one_or_none()

	async def create_prompt_version(self, prompt_id: str, payload: PromptVersionCreate) -> PromptVersion:
		async with SessionLocal() as s:
			res = await s.execute(
				select(func.coalesce(func.max(PromptVersion.version), 0)).where(PromptVersion.prompt_id == prompt_id)
			)
			next_ver = res.scalar_one() + 1
			pv = PromptVersion(prompt_id=prompt_id, version=next_ver, **payload.model_dump())
			s.add(pv)
			await s.commit()
			await s.refresh(pv)
			return pv

	async def get_latest_version(self, prompt_id: str) -> Optional[PromptVersion]:
		async with SessionLocal() as s:
			res = await s.execute(
				select(PromptVersion)
				.where(PromptVersion.prompt_id == prompt_id)
				.order_by(PromptVersion.version.desc())
				.limit(1)
			)
			return res.scalar_one_or_none()

	async def get_version(self, prompt_id: str, version: int) -> Optional[PromptVersion]:
		async with SessionLocal() as s:
			res = await s.execute(
				select(PromptVersion).where(PromptVersion.prompt_id == prompt_id, PromptVersion.version == version)
			)
			return res.scalar_one_or_none()


