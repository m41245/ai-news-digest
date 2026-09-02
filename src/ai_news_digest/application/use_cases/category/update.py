from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from ai_news_digest.core.exceptions import ResourceNotFoundError

if TYPE_CHECKING:
    from ai_news_digest.domain.models.category import Category
    from ai_news_digest.domain.ports.category_repository import CategoryRepository


@dataclass(slots=True, frozen=True)
class UpdateCategoryRequest:
    """
    Request DTO for updating an existing category.
    """

    id: UUID
    name: str | None = None
    description: str | None = None


class UpdateCategoryUseCase:
    """
    Application use case responsible for updating an existing category.
    """

    def __init__(
        self,
        repository: CategoryRepository,
    ) -> None:
        self._repository = repository

    async def execute(
        self,
        request: UpdateCategoryRequest,
    ) -> Category:
        """
        Update an existing category and return the updated representation.
        """
        category = await self._repository.get_by_id(request.id)

        if category is None:
            raise ResourceNotFoundError(f"Category {request.id} not found.")

        if request.name is not None:
            category.name = request.name

        if request.description is not None:
            category.description = request.description

        updated = await self._repository.update(category)

        return updated
