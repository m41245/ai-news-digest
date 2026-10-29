from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_news_digest.core.exceptions import ResourceNotFoundError
from ai_news_digest.domain.models.company import Company
from ai_news_digest.domain.ports.company_repository import CompanyRepository
from ai_news_digest.infrastructure.database.mappers.company_mapper import (
    CompanyMapper,
    _slugify,
)
from ai_news_digest.infrastructure.database.models.company_model import CompanyModel
from ai_news_digest.infrastructure.database.repositories.base_repository import (
    BaseRepository,
)


class SqlAlchemyCompanyRepository(BaseRepository[CompanyModel], CompanyRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self._session = session

    async def get_by_id(self, company_id: str) -> Any | None:
        result = await self._session.execute(
            select(CompanyModel).where(CompanyModel.id == company_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return CompanyMapper.to_domain(model)

    async def get_by_slug(self, slug: str) -> Any | None:
        result = await self._session.execute(
            select(CompanyModel).where(CompanyModel.slug == _slugify(slug))
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return CompanyMapper.to_domain(model)

    async def list_by_ids(self, company_ids: list[str]) -> list[Any]:
        result = await self._session.execute(
            select(CompanyModel).where(CompanyModel.id.in_(company_ids))
        )
        return [CompanyMapper.to_domain(m) for m in result.scalars().all()]

    async def list_all(self) -> list[Any]:
        result = await self._session.execute(select(CompanyModel))
        return [CompanyMapper.to_domain(m) for m in result.scalars().all()]

    async def list_all_with_counts(self) -> list[Any]:
        from ai_news_digest.infrastructure.database.models.article_company_model import (
            ArticleCompanyModel,
        )

        statement = (
            select(
                CompanyModel,
                func.count(ArticleCompanyModel.article_id).label("article_count"),
            )
            .outerjoin(
                ArticleCompanyModel,
                CompanyModel.id == ArticleCompanyModel.company_id,
            )
            .group_by(CompanyModel.id)
            .order_by(CompanyModel.name)
        )
        result = await self._session.execute(statement)
        rows = result.all()
        output: list[Any] = []
        for company_model, article_count in rows:
            company = CompanyMapper.to_domain(company_model)
            company.article_count = article_count or 0
            output.append(company)
        return output

    async def create(self, company: Any) -> Any:
        if isinstance(company, CompanyModel):
            model = company
            if not getattr(model, "slug", None):
                model.slug = _slugify(model.name)
        elif isinstance(company, Company):
            model = CompanyMapper.to_model(company)
        else:
            model = CompanyModel(
                id=str(getattr(company, "id", None) or __import__("uuid").uuid4()),
                name=company.name,
                slug=_slugify(company.name),
            )
        self._session.add(model)
        await self._flush()
        return CompanyMapper.to_domain(model)

    async def update(self, company: Any) -> Any:
        if not isinstance(company, Company):
            raise TypeError("CompanyRepository.update expects a Company domain model")
        result = await self._session.execute(
            select(CompanyModel).where(CompanyModel.id == str(company.id))
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise ResourceNotFoundError(f"Company with id '{company.id}' was not found.")
        CompanyMapper.update_model(model, company)
        await self._flush()
        return CompanyMapper.to_domain(model)

    async def delete(self, company_id: str) -> None:
        result = await self._session.execute(
            select(CompanyModel).where(CompanyModel.id == company_id)
        )
        model = result.scalar_one_or_none()
        if model is not None:
            await self._session.delete(model)
            await self._flush()


__all__ = ["SqlAlchemyCompanyRepository"]
