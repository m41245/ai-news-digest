"""
Unit tests for CategoryMapper.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from ai_news_digest.domain.models.category import Category
from ai_news_digest.infrastructure.database.mappers.category_mapper import CategoryMapper
from ai_news_digest.infrastructure.database.models.category_model import CategoryModel


@pytest.fixture
def sample_category() -> Category:
    """Create a sample Category domain object."""
    return Category.create(
        name="Technology",
        description="Technology news and updates",
    )


@pytest.fixture
def sample_category_model() -> CategoryModel:
    """Create a sample CategoryModel ORM entity."""
    model = CategoryModel(
        id=str(uuid4()),
        name="Technology",
        description="Technology news and updates",
    )
    return model


def test_category_mapper_to_model(sample_category: Category) -> None:
    """Test converting domain Category to ORM CategoryModel."""
    model = CategoryMapper.to_model(sample_category)

    assert isinstance(model, CategoryModel)
    assert str(sample_category.id) == model.id
    assert sample_category.name == model.name
    assert sample_category.description == model.description


def test_category_mapper_to_domain(sample_category_model: CategoryModel) -> None:
    """Test converting ORM CategoryModel to domain Category."""
    category = CategoryMapper.to_domain(sample_category_model)

    assert isinstance(category, Category)
    assert category.id == UUID(sample_category_model.id)
    assert category.name == sample_category_model.name
    assert category.description == sample_category_model.description


def test_category_mapper_update_model(
    sample_category: Category, sample_category_model: CategoryModel
) -> None:
    """Test updating an existing ORM model from domain Category."""
    CategoryMapper.update_model(sample_category_model, sample_category)

    assert sample_category_model.name == sample_category.name
    assert sample_category_model.description == sample_category.description


def test_category_mapper_to_model_with_empty_description(sample_category: Category) -> None:
    """Test converting domain Category with empty description."""
    sample_category.description = ""

    model = CategoryMapper.to_model(sample_category)

    assert model.description == ""


def test_category_mapper_to_domain_with_empty_description() -> None:
    """Test converting ORM CategoryModel with empty description."""
    model = CategoryModel(
        id=str(uuid4()),
        name="Technology",
        description="",
    )

    category = CategoryMapper.to_domain(model)

    assert category.description == ""
