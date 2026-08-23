"""
Unit tests for DigestMapper.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from ai_news_digest.domain.enums.digest_format import DigestFormat
from ai_news_digest.domain.models.digest import Digest
from ai_news_digest.infrastructure.database.mappers.digest_mapper import DigestMapper
from ai_news_digest.infrastructure.database.models.digest_model import DigestModel


@pytest.fixture
def sample_digest() -> Digest:
    """Create a sample Digest domain object."""
    return Digest.create(
        title="Test Digest",
        content="Test content",
        digest_format=DigestFormat.MARKDOWN,
        article_ids=[uuid4(), uuid4()],
    )


@pytest.fixture
def sample_digest_model() -> DigestModel:
    """Create a sample DigestModel ORM entity."""
    model = DigestModel(
        id=str(uuid4()),
        title="Test Digest",
        content="Test content",
        format=DigestFormat.MARKDOWN,
        generated_at=datetime.now(UTC),
    )
    return model


def test_digest_mapper_to_model(sample_digest: Digest) -> None:
    """Test converting domain Digest to ORM DigestModel."""
    model = DigestMapper.to_model(sample_digest)

    assert isinstance(model, DigestModel)
    assert str(sample_digest.id) == model.id
    assert sample_digest.title == model.title
    assert sample_digest.content == model.content
    assert sample_digest.format == model.format
    assert sample_digest.generated_at == model.generated_at


def test_digest_mapper_to_domain(sample_digest_model: DigestModel) -> None:
    """Test converting ORM DigestModel to domain Digest."""
    digest = DigestMapper.to_domain(sample_digest_model)

    assert isinstance(digest, Digest)
    assert digest.id == UUID(sample_digest_model.id)
    assert digest.title == sample_digest_model.title
    assert digest.content == sample_digest_model.content
    assert digest.format == sample_digest_model.format
    assert digest.generated_at == sample_digest_model.generated_at


def test_digest_mapper_to_domain_with_article_ids() -> None:
    """Test converting ORM DigestModel with loaded digest_articles to domain Digest."""
    from ai_news_digest.infrastructure.database.models.digest_article_model import (
        DigestArticleModel,
    )

    model = DigestModel(
        id=str(uuid4()),
        title="Test Digest",
        content="Test content",
        format=DigestFormat.MARKDOWN,
        generated_at=datetime.now(UTC),
    )

    # Simulate loaded relationship
    article_id_1 = str(uuid4())
    article_id_2 = str(uuid4())
    link1 = DigestArticleModel(digest_id=model.id, article_id=article_id_1)
    link2 = DigestArticleModel(digest_id=model.id, article_id=article_id_2)
    model.digest_articles = [link1, link2]

    digest = DigestMapper.to_domain(model)

    assert len(digest.article_ids) == 2
    assert article_id_1 in [str(aid) for aid in digest.article_ids]
    assert article_id_2 in [str(aid) for aid in digest.article_ids]


def test_digest_mapper_to_domain_without_article_ids(sample_digest_model: DigestModel) -> None:
    """Test converting ORM DigestModel without loaded digest_articles to domain Digest."""
    sample_digest_model.digest_articles = []

    digest = DigestMapper.to_domain(sample_digest_model)

    assert len(digest.article_ids) == 0


def test_digest_mapper_update_model(
    sample_digest: Digest, sample_digest_model: DigestModel
) -> None:
    """Test updating an existing ORM model from domain Digest."""
    sample_digest.title = "Updated Title"
    sample_digest.content = "Updated content"

    DigestMapper.update_model(sample_digest_model, sample_digest)

    assert sample_digest_model.title == sample_digest.title
    assert sample_digest_model.content == sample_digest.content
    assert sample_digest_model.format == sample_digest.format
    assert sample_digest_model.generated_at == sample_digest.generated_at


def test_digest_mapper_to_model_html_format(sample_digest: Digest) -> None:
    """Test converting domain Digest with HTML format."""
    sample_digest.format = DigestFormat.HTML

    model = DigestMapper.to_model(sample_digest)

    assert model.format == DigestFormat.HTML


def test_digest_mapper_to_model_pdf_format(sample_digest: Digest) -> None:
    """Test converting domain Digest with PDF format."""
    sample_digest.format = DigestFormat.PDF

    model = DigestMapper.to_model(sample_digest)

    assert model.format == DigestFormat.PDF


def test_digest_mapper_to_domain_html_format() -> None:
    """Test converting ORM DigestModel with HTML format."""
    model = DigestModel(
        id=str(uuid4()),
        title="Test Digest",
        content="Test content",
        format=DigestFormat.HTML,
        generated_at=datetime.now(UTC),
    )

    digest = DigestMapper.to_domain(model)

    assert digest.format == DigestFormat.HTML


def test_digest_mapper_to_domain_pdf_format() -> None:
    """Test converting ORM DigestModel with PDF format."""
    model = DigestModel(
        id=str(uuid4()),
        title="Test Digest",
        content="Test content",
        format=DigestFormat.PDF,
        generated_at=datetime.now(UTC),
    )

    digest = DigestMapper.to_domain(model)

    assert digest.format == DigestFormat.PDF
