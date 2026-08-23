from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_news_digest.core.exceptions import ResourceNotFoundError
from ai_news_digest.domain.models.category import Category
from ai_news_digest.domain.ports.category_repository import (
    CategoryRepository as CategoryRepositoryPort,
)
from ai_news_digest.infrastructure.database.mappers.category_mapper import (
    CategoryMapper,
)
from ai_news_digest.infrastructure.database.models.category_model import (
    CategoryModel,
)
from ai_news_digest.infrastructure.database.repositories.base_repository import (
    BaseRepository,
)


class CategoryRepository(
    BaseRepository[CategoryModel],
    CategoryRepositoryPort,
):
    """SQLAlchemy implementation of the CategoryRepository port."""

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        super().__init__(session)

    async def create(
        self,
        category: Category,
    ) -> Category:
        """Persist a new category."""
        model = CategoryMapper.to_model(category)
        model = await self._add_and_refresh(model)
        return CategoryMapper.to_domain(model)

    async def get_by_id(
        self,
        category_id: UUID,
    ) -> Category | None:
        """Retrieve a category by its identifier."""
        statement = select(CategoryModel).where(CategoryModel.id == str(category_id))

        result = await self._session.execute(statement)

        model = result.scalar_one_or_none()

        if model is None:
            return None

        return CategoryMapper.to_domain(model)

    async def get_by_name(
        self,
        name: str,
    ) -> Category | None:
        """Retrieve a category by its name."""
        statement = select(CategoryModel).where(CategoryModel.name == name)

        result = await self._session.execute(statement)

        model = result.scalar_one_or_none()

        if model is None:
            return None

        return CategoryMapper.to_domain(model)

    async def list_all(
        self,
    ) -> list[Category]:
        """Return all categories ordered by name."""
        statement = select(CategoryModel).order_by(CategoryModel.name.asc())

        result = await self._session.execute(statement)

        models = result.scalars().all()

        return [CategoryMapper.to_domain(model) for model in models]

    async def update(
        self,
        category: Category,
    ) -> Category:
        """Update an existing category."""
        statement = select(CategoryModel).where(CategoryModel.id == str(category.id))

        result = await self._session.execute(statement)

        model = result.scalar_one_or_none()

        if model is None:
            raise ResourceNotFoundError(f"Category with id '{category.id}' was not found.")

        CategoryMapper.update_model(
            model,
            category,
        )

        await self._commit()

        model = await self._refresh(model)

        return CategoryMapper.to_domain(model)

    async def delete(
        self,
        category_id: UUID,
    ) -> None:
        """Delete a category by its identifier."""
        statement = select(CategoryModel).where(CategoryModel.id == str(category_id))

        result = await self._session.execute(statement)

        model = result.scalar_one_or_none()

        if model is None:
            return

        await self._delete(model)
