"""
Unit tests for Category domain model.
"""

from __future__ import annotations

from datetime import UTC, datetime

from ai_news_digest.domain.models.category import Category


def test_category_create_with_description() -> None:
    """Test Category.create with description."""
    category = Category.create(
        name="Technology",
        description="Tech news and updates",
    )

    assert category.id is not None
    assert category.name == "Technology"
    assert category.description == "Tech news and updates"
    assert category.created_at is not None


def test_category_create_without_description() -> None:
    """Test Category.create without description."""
    category = Category.create(name="Technology")

    assert category.name == "Technology"
    assert category.description is None


def test_category_create_generates_id() -> None:
    """Test Category.create generates unique IDs."""
    category1 = Category.create(name="Technology")
    category2 = Category.create(name="Science")

    assert category1.id != category2.id


def test_category_create_sets_created_at() -> None:
    """Test Category.create sets created_at to current time."""
    before = datetime.now(UTC)
    category = Category.create(name="Technology")
    after = datetime.now(UTC)

    assert before <= category.created_at <= after
