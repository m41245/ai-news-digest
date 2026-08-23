"""
Unit tests for ArticleMapper.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from ai_news_digest.domain.enums.article_status import ArticleStatus
from ai_news_digest.domain.models.article import Article
from ai_news_digest.infrastructure.database.mappers.article_mapper import ArticleMapper
from ai_news_digest.infrastructure.database.models.article_model import ArticleModel


@pytest.fixture
def sample_article() -> Article:
    """Create a sample Article domain object."""
    return Article.create(
        title="Test Article",
        url="https://example.com/article",
        summary="Test summary",
        content="Test content",
        source_id=uuid4(),
        published_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_article_model() -> ArticleModel:
    """Create a sample ArticleModel ORM entity."""
    model = ArticleModel(
        id=str(uuid4()),
        source_id=str(uuid4()),
        title="Test Article",
        url="https://example.com/article",
        summary="Test summary",
        content="Test content",
        status=ArticleStatus.NEW,
        published_at=datetime.now(UTC),
        fetched_at=datetime.now(UTC),
    )
    return model


def test_article_mapper_to_model(sample_article: Article) -> None:
    """Test converting domain Article to ORM ArticleModel."""
    model = ArticleMapper.to_model(sample_article)

    assert isinstance(model, ArticleModel)
    assert str(sample_article.id) == model.id
    assert str(sample_article.source_id) == model.source_id
    assert sample_article.title == model.title
    assert sample_article.url == model.url
    assert sample_article.summary == model.summary
    assert sample_article.content == model.content
    assert sample_article.status == model.status


def test_article_mapper_to_model_with_category(sample_article: Article) -> None:
    """Test converting domain Article with category to ORM ArticleModel."""
    sample_article.category_id = uuid4()

    model = ArticleMapper.to_model(sample_article)

    assert model.category_id == str(sample_article.category_id)


def test_article_mapper_to_model_without_category(sample_article: Article) -> None:
    """Test converting domain Article without category to ORM ArticleModel."""
    sample_article.category_id = None

    model = ArticleMapper.to_model(sample_article)

    assert model.category_id is None


def test_article_mapper_to_domain(sample_article_model: ArticleModel) -> None:
    """Test converting ORM ArticleModel to domain Article."""
    article = ArticleMapper.to_domain(sample_article_model)

    assert isinstance(article, Article)
    assert article.id == UUID(sample_article_model.id)
    assert article.source_id == UUID(sample_article_model.source_id)
    assert article.title == sample_article_model.title
    assert article.url == sample_article_model.url
    assert article.summary == sample_article_model.summary
    assert article.content == sample_article_model.content
    assert article.status == sample_article_model.status


def test_article_mapper_to_domain_with_category() -> None:
    """Test converting ORM ArticleModel with category to domain Article."""
    model = ArticleModel(
        id=str(uuid4()),
        source_id=str(uuid4()),
        category_id=str(uuid4()),
        title="Test Article",
        url="https://example.com/article",
        summary="Test summary",
        content="Test content",
        status=ArticleStatus.NEW,
        published_at=datetime.now(UTC),
        fetched_at=datetime.now(UTC),
    )

    article = ArticleMapper.to_domain(model)

    assert article.category_id is not None
    assert article.category_id == UUID(model.category_id)


def test_article_mapper_to_domain_without_category(sample_article_model: ArticleModel) -> None:
    """Test converting ORM ArticleModel without category to domain Article."""
    sample_article_model.category_id = None

    article = ArticleMapper.to_domain(sample_article_model)

    assert article.category_id is None


def test_article_mapper_update_model(
    sample_article: Article, sample_article_model: ArticleModel
) -> None:
    """Test updating an existing ORM model from domain Article."""
    ArticleMapper.update_model(sample_article_model, sample_article)

    assert sample_article_model.source_id == str(sample_article.source_id)
    assert sample_article_model.title == sample_article.title
    assert sample_article_model.url == sample_article.url
    assert sample_article_model.summary == sample_article.summary
    assert sample_article_model.content == sample_article.content
    assert sample_article_model.status == sample_article.status


def test_article_mapper_update_model_with_category(
    sample_article: Article, sample_article_model: ArticleModel
) -> None:
    """Test updating model with category_id."""
    sample_article.category_id = uuid4()

    ArticleMapper.update_model(sample_article_model, sample_article)

    assert sample_article_model.category_id == str(sample_article.category_id)


def test_article_mapper_update_model_without_category(
    sample_article: Article, sample_article_model: ArticleModel
) -> None:
    """Test updating model without category_id."""
    sample_article.category_id = None
    sample_article_model.category_id = str(uuid4())

    ArticleMapper.update_model(sample_article_model, sample_article)

    assert sample_article_model.category_id is None
