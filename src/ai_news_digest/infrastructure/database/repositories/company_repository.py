from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_news_digest.domain.ports.company_repository import CompanyRepository
from ai_news_digest.infrastructure.database.models.company_model import CompanyModel


class SqlAlchemyCompanyRepository(CompanyRepository):
    """
    SQLAlchemy implementation of CompanyRepository.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, company_id: str) -> Any | None:
        result = await self._session.execute(
            select(CompanyModel).where(CompanyModel.id == company_id)
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Any | None:
        result = await self._session.execute(select(CompanyModel).where(CompanyModel.name == slug))
        return result.scalar_one_or_none()

    async def list_by_ids(self, company_ids: list[str]) -> list[Any]:
        result = await self._session.execute(
            select(CompanyModel).where(CompanyModel.id.in_(company_ids))
        )
        return list(result.scalars().all())

    async def create(self, company: Any) -> Any:
        self._session.add(company)
        await self._session.flush()
        return company

    async def update(self, company: Any) -> Any:
        await self._session.flush()
        return company

    async def delete(self, company_id: str) -> None:
        result = await self._session.execute(
            select(CompanyModel).where(CompanyModel.id == company_id)
        )
        model = result.scalar_one_or_none()
        if model is not None:
            await self._session.delete(model)
