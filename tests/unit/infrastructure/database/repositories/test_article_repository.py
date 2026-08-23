"""
Unit tests for ArticleRepository.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from ai_news_digest.application.services.rss.parser.models import ParsedArticle
from ai_news_digest.core.exceptions import ResourceNotFoundError
from ai_news_digest.domain.models.article import Article
from ai_news_digest.infrastructure.database.repositories.article_repository import ArticleRepository


@pytest.fixture
def mock_session() -> AsyncMock:
    """Create a mock AsyncSession."""
    session = AsyncMock()
    return session


@pytest.fixture
def repository(mock_session: AsyncMock) -> ArticleRepository:
    """Create an ArticleRepository instance."""
    return ArticleRepository(mock_session)


@pytest.fixture
def sample_article() -> Article:
    """Create a sample Article."""
    return Article.create(
        title="Test Article",
        url="https://example.com/article",
        summary="Test summary",
        content="Test content",
        source_id=uuid4(),
        published_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_article_repository_create(
    repository: ArticleRepository, mock_session: AsyncMock, sample_article: Article
) -> None:
    """Test create method."""
    mock_result = MagicMock()
    mock_session.execute.return_value = mock_result
    mock_session.refresh = AsyncMock()

    with patch.object(repository, "_add_and_refresh", new_callable=AsyncMock) as mock_add_refresh:
        mock_model = MagicMock()
        mock_model.id = str(sample_article.id)
        mock_add_refresh.return_value = mock_model

        with patch(
            "ai_news_digest.infrastructure.database.repositories.article_repository.ArticleMapper.to_model"
        ) as mock_to_model:
            mock_to_model.return_value = mock_model

            with patch(
                "ai_news_digest.infrastructure.database.repositories.article_repository.ArticleMapper.to_domain"
            ) as mock_to_domain:
                mock_to_domain.return_value = sample_article

                result = await repository.create(sample_article)

                assert result == sample_article


@pytest.mark.asyncio
async def test_article_repository_create_from_parsed(repository: ArticleRepository) -> None:
    """Test create_from_parsed method."""
    source_id = uuid4()
    parsed_article = ParsedArticle(
        title="Parsed Article",
        url="https://example.com/parsed",
        summary="Parsed summary",
        published_at=datetime.now(UTC),
    )

    with patch.object(repository, "create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = MagicMock()

        await repository.create_from_parsed(source_id=source_id, article=parsed_article)

        mock_create.assert_called_once()


@pytest.mark.asyncio
async def test_article_repository_get_by_id_found(
    repository: ArticleRepository, mock_session: AsyncMock
) -> None:
    """Test get_by_id when article is found."""
    article_id = uuid4()
    mock_result = MagicMock()
    mock_model = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_model
    mock_session.execute.return_value = mock_result

    with patch(
        "ai_news_digest.infrastructure.database.repositories.article_repository.ArticleMapper.to_domain"
    ) as mock_to_domain:
        mock_domain = MagicMock()
        mock_to_domain.return_value = mock_domain

        result = await repository.get_by_id(article_id)

        assert result == mock_domain


@pytest.mark.asyncio
async def test_article_repository_get_by_id_not_found(
    repository: ArticleRepository, mock_session: AsyncMock
) -> None:
    """Test get_by_id when article is not found."""
    article_id = uuid4()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    result = await repository.get_by_id(article_id)

    assert result is None


@pytest.mark.asyncio
async def test_article_repository_get_by_url_found(
    repository: ArticleRepository, mock_session: AsyncMock
) -> None:
    """Test get_by_url when article is found."""
    mock_result = MagicMock()
    mock_model = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_model
    mock_session.execute.return_value = mock_result

    with patch(
        "ai_news_digest.infrastructure.database.repositories.article_repository.ArticleMapper.to_domain"
    ) as mock_to_domain:
        mock_domain = MagicMock()
        mock_to_domain.return_value = mock_domain

        result = await repository.get_by_url("https://example.com/article")

        assert result == mock_domain


@pytest.mark.asyncio
async def test_article_repository_get_by_url_not_found(
    repository: ArticleRepository, mock_session: AsyncMock
) -> None:
    """Test get_by_url when article is not found."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    result = await repository.get_by_url("https://example.com/article")

    assert result is None


@pytest.mark.asyncio
async def test_article_repository_list_recent(
    repository: ArticleRepository, mock_session: AsyncMock
) -> None:
    """Test list_recent method."""
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_models = [MagicMock(), MagicMock()]
    mock_scalars.all.return_value = mock_models
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    with patch(
        "ai_news_digest.infrastructure.database.repositories.article_repository.ArticleMapper.to_domain"
    ) as mock_to_domain:
        mock_to_domain.side_effect = lambda m: m

        result = await repository.list_recent(limit=10)

        assert len(result) == 2


@pytest.mark.asyncio
async def test_article_repository_list_digest_eligible(
    repository: ArticleRepository, mock_session: AsyncMock
) -> None:
    """Test list_digest_eligible method."""
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_models = [MagicMock(), MagicMock()]
    mock_scalars.all.return_value = mock_models
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    with patch(
        "ai_news_digest.infrastructure.database.repositories.article_repository.ArticleMapper.to_domain"
    ) as mock_to_domain:
        mock_to_domain.side_effect = lambda m: m

        result = await repository.list_digest_eligible(limit=10)

        assert len(result) == 2


@pytest.mark.asyncio
async def test_article_repository_list_digest_eligible_no_limit(
    repository: ArticleRepository, mock_session: AsyncMock
) -> None:
    """Test list_digest_eligible without limit."""
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_models = [MagicMock()]
    mock_scalars.all.return_value = mock_models
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    with patch(
        "ai_news_digest.infrastructure.database.repositories.article_repository.ArticleMapper.to_domain"
    ) as mock_to_domain:
        mock_to_domain.side_effect = lambda m: m

        result = await repository.list_digest_eligible(limit=None)

        assert len(result) == 1


@pytest.mark.asyncio
async def test_article_repository_update_found(
    repository: ArticleRepository, mock_session: AsyncMock, sample_article: Article
) -> None:
    """Test update when article is found."""
    mock_result = MagicMock()
    mock_model = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_model
    mock_session.execute.return_value = mock_result
    mock_session.refresh = AsyncMock()

    with (
        patch(
            "ai_news_digest.infrastructure.database.repositories.article_repository.ArticleMapper.update_model"
        ),
        patch(
            "ai_news_digest.infrastructure.database.repositories.article_repository.ArticleMapper.to_domain"
        ) as mock_to_domain,
    ):
        mock_to_domain.return_value = sample_article

        result = await repository.update(sample_article)

        assert result == sample_article


@pytest.mark.asyncio
async def test_article_repository_update_not_found(
    repository: ArticleRepository, mock_session: AsyncMock, sample_article: Article
) -> None:
    """Test update when article is not found."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    with pytest.raises(ResourceNotFoundError, match="was not found"):
        await repository.update(sample_article)


@pytest.mark.asyncio
async def test_article_repository_delete_found(
    repository: ArticleRepository, mock_session: AsyncMock
) -> None:
    """Test delete when article is found."""
    article_id = uuid4()
    mock_result = MagicMock()
    mock_model = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_model
    mock_session.execute.return_value = mock_result

    with patch.object(repository, "_delete", new_callable=AsyncMock):
        await repository.delete(article_id)


@pytest.mark.asyncio
async def test_article_repository_delete_not_found(
    repository: ArticleRepository, mock_session: AsyncMock
) -> None:
    """Test delete when article is not found."""
    article_id = uuid4()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    await repository.delete(article_id)  # Should not raise
