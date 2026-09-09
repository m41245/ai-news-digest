"""
Unit tests for AnalyzeAndMaterializeUseCase.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from ai_news_digest.application.use_cases.article.analyze_and_materialize import (
    AnalyzeAndMaterializeUseCase,
)
from ai_news_digest.domain.enums.article_status import ArticleStatus
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.models.category import Category
from ai_news_digest.domain.models.company import Company
from ai_news_digest.domain.models.topic import Topic


@pytest.fixture
def mock_analyze_use_case() -> MagicMock:
    """Mock AnalyzeArticleUseCase for testing."""
    use_case = MagicMock()
    use_case.execute = AsyncMock()
    return use_case


@pytest.fixture
def sample_article() -> Article:
    """Create a sample article for testing."""
    article = Article.create(
        title="Test Article",
        url="https://example.com/article",
        summary="Original summary",
        content="Full article content here",
        source_id=uuid4(),
        published_at=datetime.now(UTC),
    )
    article.importance_score = 0.9
    article.confidence = 0.8
    article.key_takeaways = ("Takeaway 1",)
    article.why_it_matters = "Important"
    article.companies = ("Acme",)
    article.topics = ("AI",)
    article.categories = ("Technology",)
    return article


async def test_analyze_and_materialize_success(
    mock_analyze_use_case: MagicMock,
    sample_article: Article,
) -> None:
    """Test successful analyze and materialize."""
    # Arrange
    mock_analyze_use_case.execute.return_value = sample_article

    company_repository = MagicMock()
    company_repository.get_by_slug = AsyncMock(return_value=None)
    company_repository.create = AsyncMock(return_value=MagicMock(id=uuid4()))
    company_repository.replace_companies = AsyncMock()

    topic_repository = MagicMock()
    topic_repository.get_by_slug = AsyncMock(return_value=None)
    topic_repository.create = AsyncMock(return_value=MagicMock(id=uuid4()))
    topic_repository.replace_topics = AsyncMock()

    category_repository = MagicMock()
    category_repository.get_by_name = AsyncMock(return_value=None)
    category_repository.create = AsyncMock(return_value=MagicMock(id=uuid4()))
    category_repository.replace_categories = AsyncMock()

    article_repository = MagicMock()
    article_repository.update = AsyncMock(return_value=sample_article)
    article_repository.replace_companies = AsyncMock()
    article_repository.replace_topics = AsyncMock()
    article_repository.replace_categories = AsyncMock()

    use_case = AnalyzeAndMaterializeUseCase(
        analyze_use_case=mock_analyze_use_case,
        article_repository=article_repository,
        company_repository=company_repository,
        topic_repository=topic_repository,
        category_repository=category_repository,
    )

    # Act
    result = await use_case.execute(sample_article)

    # Assert
    assert result.status == ArticleStatus.ANALYZED
    mock_analyze_use_case.execute.assert_called_once_with(sample_article)
    article_repository.update.assert_called_once_with(sample_article)


async def test_analyze_and_materialize_existing_entities(
    mock_analyze_use_case: MagicMock,
    sample_article: Article,
) -> None:
    """Test materialize reuses existing companies, topics, and categories."""
    # Arrange
    mock_analyze_use_case.execute.return_value = sample_article

    existing_company = Company.create(name="Acme")
    existing_topic = Topic.create(name="AI")
    existing_category = Category.create(name="Technology")

    company_repository = MagicMock()
    company_repository.get_by_slug = AsyncMock(return_value=existing_company)
    company_repository.create = AsyncMock()
    company_repository.replace_companies = AsyncMock()

    topic_repository = MagicMock()
    topic_repository.get_by_slug = AsyncMock(return_value=existing_topic)
    topic_repository.create = AsyncMock()
    topic_repository.replace_topics = AsyncMock()

    category_repository = MagicMock()
    category_repository.get_by_name = AsyncMock(return_value=existing_category)
    category_repository.create = AsyncMock()
    category_repository.replace_categories = AsyncMock()

    article_repository = MagicMock()
    article_repository.update = AsyncMock(return_value=sample_article)
    article_repository.replace_companies = AsyncMock()
    article_repository.replace_topics = AsyncMock()
    article_repository.replace_categories = AsyncMock()

    use_case = AnalyzeAndMaterializeUseCase(
        analyze_use_case=mock_analyze_use_case,
        article_repository=article_repository,
        company_repository=company_repository,
        topic_repository=topic_repository,
        category_repository=category_repository,
    )

    # Act
    result = await use_case.execute(sample_article)

    # Assert
    assert result.status == ArticleStatus.ANALYZED
    company_repository.create.assert_not_called()
    topic_repository.create.assert_not_called()
    category_repository.create.assert_not_called()


async def test_analyze_and_materialize_no_entities(
    mock_analyze_use_case: MagicMock,
    sample_article: Article,
) -> None:
    """Test materialize handles articles with no entities."""
    # Arrange
    article = Article.create(
        title="Test Article",
        url="https://example.com/article",
        summary="Original summary",
        content="Full article content here",
        source_id=uuid4(),
        published_at=datetime.now(UTC),
    )
    article.importance_score = 0.5
    article.confidence = 0.5
    article.companies = ()
    article.topics = ()
    article.categories = ()

    mock_analyze_use_case.execute.return_value = article

    company_repository = MagicMock()
    company_repository.get_by_slug = AsyncMock()
    company_repository.create = AsyncMock()
    company_repository.replace_companies = AsyncMock()

    topic_repository = MagicMock()
    topic_repository.get_by_slug = AsyncMock()
    topic_repository.create = AsyncMock()
    topic_repository.replace_topics = AsyncMock()

    category_repository = MagicMock()
    category_repository.get_by_name = AsyncMock()
    category_repository.create = AsyncMock()
    category_repository.replace_categories = AsyncMock()

    article_repository = MagicMock()
    article_repository.update = AsyncMock(return_value=article)

    use_case = AnalyzeAndMaterializeUseCase(
        analyze_use_case=mock_analyze_use_case,
        article_repository=article_repository,
        company_repository=company_repository,
        topic_repository=topic_repository,
        category_repository=category_repository,
    )

    # Act
    result = await use_case.execute(article)

    # Assert
    assert result.status == ArticleStatus.ANALYZED
    company_repository.replace_companies.assert_not_called()
    topic_repository.replace_topics.assert_not_called()
    category_repository.replace_categories.assert_not_called()
