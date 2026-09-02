"""
Factory for creating Category domain entities in tests.
"""

from __future__ import annotations

from ai_news_digest.domain.models.category import Category


def create_category(
    *,
    entity_id: str | None = None,
    name: str = "Test Category",
    description: str | None = "Test description",
) -> Category:
    """
    Create a test Category domain entity.

    Args:
        entity_id: Optional category ID
        name: Category name
        description: Optional description

    Returns:
        Category domain entity
    """
    category = Category.create(
        name=name,
        description=description,
    )

    if entity_id is not None:
        object.__setattr__(category, "id", entity_id)
    return category
