"""
Unit tests for SourceMapper.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from ai_news_digest.domain.models.source import Source
from ai_news_digest.infrastructure.database.mappers.source_mapper import SourceMapper
from ai_news_digest.infrastructure.database.models.source_model import SourceModel


@pytest.fixture
def sample_source() -> Source:
    """Create a sample Source domain object."""
    return Source.create(
        name="Test Source",
        feed_url="https://example.com/feed.xml",
        website_url="https://example.com",
        description="Test description",
    )


@pytest.fixture
def sample_source_model() -> SourceModel:
    """Create a sample SourceModel ORM entity."""
    model = SourceModel(
        id=str(uuid4()),
        name="Test Source",
        feed_url="https://example.com/feed.xml",
        website_url="https://example.com",
        description="Test description",
        is_active=True,
        created_at=datetime.now(UTC),
    )
    return model


def test_source_mapper_to_model(sample_source: Source) -> None:
    """Test converting domain Source to ORM SourceModel."""
    model = SourceMapper.to_model(sample_source)

    assert isinstance(model, SourceModel)
    assert str(sample_source.id) == model.id
    assert sample_source.name == model.name
    assert sample_source.feed_url == model.feed_url
    assert sample_source.website_url == model.website_url
    assert sample_source.description == model.description
    assert sample_source.is_active == model.is_active


def test_source_mapper_to_domain(sample_source_model: SourceModel) -> None:
    """Test converting ORM SourceModel to domain Source."""
    source = SourceMapper.to_domain(sample_source_model)

    assert isinstance(source, Source)
    assert source.id == UUID(sample_source_model.id)
    assert source.name == sample_source_model.name
    assert source.feed_url == sample_source_model.feed_url
    assert source.website_url == sample_source_model.website_url
    assert source.description == sample_source_model.description
    assert source.is_active == sample_source_model.is_active


def test_source_mapper_update_model(
    sample_source: Source, sample_source_model: SourceModel
) -> None:
    """Test updating an existing ORM model from domain Source."""
    sample_source.name = "Updated Name"
    sample_source.feed_url = "https://updated.com/feed.xml"

    SourceMapper.update_model(sample_source_model, sample_source)

    assert sample_source_model.name == sample_source.name
    assert sample_source_model.feed_url == sample_source.feed_url
    assert sample_source_model.website_url == sample_source.website_url
    assert sample_source_model.description == sample_source.description
    assert sample_source_model.is_active == sample_source.is_active


def test_source_mapper_to_model_with_none_website_url(sample_source: Source) -> None:
    """Test converting domain Source with None website_url."""
    sample_source.website_url = None

    model = SourceMapper.to_model(sample_source)

    assert model.website_url is None


def test_source_mapper_to_model_with_none_description(sample_source: Source) -> None:
    """Test converting domain Source with None description."""
    sample_source.description = None

    model = SourceMapper.to_model(sample_source)

    assert model.description is None


def test_source_mapper_to_domain_with_none_website_url() -> None:
    """Test converting ORM SourceModel with None website_url."""
    model = SourceModel(
        id=str(uuid4()),
        name="Test Source",
        feed_url="https://example.com/feed.xml",
        website_url=None,
        description="Test description",
        is_active=True,
        created_at=datetime.now(UTC),
    )

    source = SourceMapper.to_domain(model)

    assert source.website_url is None


def test_source_mapper_to_domain_with_none_description() -> None:
    """Test converting ORM SourceModel with None description."""
    model = SourceModel(
        id=str(uuid4()),
        name="Test Source",
        feed_url="https://example.com/feed.xml",
        website_url="https://example.com",
        description=None,
        is_active=True,
        created_at=datetime.now(UTC),
    )

    source = SourceMapper.to_domain(model)

    assert source.description is None


def test_source_mapper_to_model_inactive(sample_source: Source) -> None:
    """Test converting inactive domain Source to ORM SourceModel."""
    sample_source.is_active = False

    model = SourceMapper.to_model(sample_source)

    assert model.is_active is False


def test_source_mapper_to_domain_inactive() -> None:
    """Test converting inactive ORM SourceModel to domain Source."""
    model = SourceModel(
        id=str(uuid4()),
        name="Test Source",
        feed_url="https://example.com/feed.xml",
        website_url="https://example.com",
        description="Test description",
        is_active=False,
        created_at=datetime.now(UTC),
    )

    source = SourceMapper.to_domain(model)

    assert source.is_active is False
