from __future__ import annotations

from uuid import UUID

from ai_news_digest.domain.models.category import Category
from ai_news_digest.infrastructure.database.models.category_model import (
    CategoryModel,
)


class CategoryMapper:
    """Maps between Category domain objects and CategoryModel ORM entities."""

    @staticmethod
    def to_model(category: Category) -> CategoryModel:
        """Convert a domain Category into an ORM CategoryModel."""
        return CategoryModel(
            id=str(category.id),
            name=category.name,
            description=category.description,
            created_at=category.created_at,
        )

    @staticmethod
    def to_domain(model: CategoryModel) -> Category:
        """Convert an ORM CategoryModel into a domain Category."""
        return Category(
            id=UUID(model.id),
            name=model.name,
            description=model.description,
            created_at=model.created_at,
        )

    @staticmethod
    def update_model(
        model: CategoryModel,
        category: Category,
    ) -> None:
        """Update an existing ORM model from a domain Category."""
        model.name = category.name
        model.description = category.description
