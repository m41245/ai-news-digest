"""
Unit tests for Category domain model.
"""

from __future__ import annotations

from uuid import UUID

from ai_news_digest.domain.models.category import Category


def test_category_creation():
    """Test that a Category can be created with valid parameters."""
    category = Category.create(
        name="Test Category",
        description="Test description",
    )

    assert isinstance(category.id, UUID)
    assert category.name == "Test Category"
    assert category.description == "Test description"
    assert category.created_at is not None


def test_category_creation_without_description():
    """Test that a Category can be created without a description."""
    category = Category.create(
        name="Test Category",
    )

    assert category.name == "Test Category"
    assert category.description is None
