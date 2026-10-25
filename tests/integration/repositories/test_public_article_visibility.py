from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from ai_news_digest.bootstrap.container import Container
from ai_news_digest.domain.enums.article_status import ArticleStatus
from ai_news_digest.domain.enums.source_status import SourceStatus
from ai_news_digest.domain.enums.source_type import SourceType
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.models.source import Source


async def _seed_source(
    container: Container,
    *,
    status: SourceStatus,
    is_active: bool,
) -> Source:
    source = Source(
        id=uuid4(),
        name=f"Source {uuid4().hex[:8]}",
        feed_url=f"https://example.com/{uuid4().hex}/feed.xml",
        website_url=None,
        description=None,
        is_active=is_active,
        source_type=SourceType.OTHER,
        status=status,
        created_at=datetime.now(UTC),
    )
    return await container.source_repository.create(source)


async def _seed_article(
    container: Container,
    source: Source,
    *,
    status: ArticleStatus,
    title: str | None = None,
    published_at: datetime | None = None,
    importance_score: float | None = None,
) -> Article:
    article = Article(
        id=uuid4(),
        title=title or f"Article {uuid4().hex[:8]}",
        url=f"https://example.com/{uuid4().hex}/article",
        summary="RSS summary",
        content="RSS content",
        source_id=source.id,
        category_id=None,
        published_at=published_at or datetime.now(UTC),
        fetched_at=datetime.now(UTC),
        status=status,
        importance_score=importance_score,
    )
    return await container.article_repository.create(article)


@pytest.mark.asyncio
async def test_public_visibility_includes_new_trusted_articles(
    db_session: AsyncSession,
) -> None:
    container = Container(db_session)

    source = await _seed_source(
        container,
        status=SourceStatus.VERIFIED,
        is_active=True,
    )
    article = await _seed_article(container, source, status=ArticleStatus.NEW)

    listed = await container.article_repository.list_public_articles()
    assert any(item.id == article.id for item in listed)

    fetched = await container.article_repository.get_public_article(article.id)
    assert fetched is not None
    assert fetched.id == article.id

    count = await container.article_repository.count_public_articles()
    assert count == 1
    assert count == len(listed)


@pytest.mark.asyncio
async def test_public_visibility_count_matches_list_total(
    db_session: AsyncSession,
) -> None:
    container = Container(db_session)

    trusted_source = await _seed_source(
        container,
        status=SourceStatus.VERIFIED,
        is_active=True,
    )
    visible_articles = [
        await _seed_article(
            container,
            trusted_source,
            status=ArticleStatus.NEW,
            published_at=datetime.now(UTC) + timedelta(minutes=index),
        )
        for index in range(3)
    ]
    await _seed_article(container, trusted_source, status=ArticleStatus.FAILED)

    untrusted_source = await _seed_source(
        container,
        status=SourceStatus.PENDING_REVIEW,
        is_active=True,
    )
    await _seed_article(container, untrusted_source, status=ArticleStatus.NEW)

    page = await container.article_repository.list_public_articles(limit=2, offset=0)
    assert len(page) == 2

    count = await container.article_repository.count_public_articles()
    assert count == 3
    assert count == len(visible_articles)

    full_list = await container.article_repository.list_public_articles()
    assert len(full_list) == count
    assert {item.id for item in full_list} == {item.id for item in visible_articles}

    filtered_list = await container.article_repository.list_public_articles(
        source_id=trusted_source.id,
    )
    filtered_count = await container.article_repository.count_public_articles(
        source_id=trusted_source.id,
    )
    assert len(filtered_list) == filtered_count == 3


@pytest.mark.asyncio
async def test_public_visibility_excludes_inactive_sources(
    db_session: AsyncSession,
) -> None:
    container = Container(db_session)

    source = await _seed_source(
        container,
        status=SourceStatus.VERIFIED,
        is_active=False,
    )
    article = await _seed_article(container, source, status=ArticleStatus.NEW)

    listed = await container.article_repository.list_public_articles()
    assert all(item.id != article.id for item in listed)

    fetched = await container.article_repository.get_public_article(article.id)
    assert fetched is None

    count = await container.article_repository.count_public_articles()
    assert count == 0


@pytest.mark.asyncio
async def test_public_visibility_excludes_pending_and_unverified_sources(
    db_session: AsyncSession,
) -> None:
    container = Container(db_session)

    for status in (SourceStatus.PENDING_REVIEW, SourceStatus.REJECTED, SourceStatus.INACTIVE):
        source = await _seed_source(
            container,
            status=status,
            is_active=True,
        )
        article = await _seed_article(container, source, status=ArticleStatus.NEW)

        listed = await container.article_repository.list_public_articles()
        assert all(item.id != article.id for item in listed)

        fetched = await container.article_repository.get_public_article(article.id)
        assert fetched is None

        count = await container.article_repository.count_public_articles()
        assert count == 0


@pytest.mark.asyncio
async def test_public_visibility_excludes_failed_articles(
    db_session: AsyncSession,
) -> None:
    container = Container(db_session)

    source = await _seed_source(
        container,
        status=SourceStatus.VERIFIED,
        is_active=True,
    )
    article = await _seed_article(container, source, status=ArticleStatus.FAILED)

    listed = await container.article_repository.list_public_articles()
    assert all(item.id != article.id for item in listed)

    fetched = await container.article_repository.get_public_article(article.id)
    assert fetched is None

    count = await container.article_repository.count_public_articles()
    assert count == 0


@pytest.mark.asyncio
async def test_public_detail_follows_list_rules(
    db_session: AsyncSession,
) -> None:
    container = Container(db_session)

    trusted_source = await _seed_source(
        container,
        status=SourceStatus.VERIFIED,
        is_active=True,
    )
    visible_article = await _seed_article(
        container,
        trusted_source,
        status=ArticleStatus.NEW,
    )
    failed_article = await _seed_article(
        container,
        trusted_source,
        status=ArticleStatus.FAILED,
    )

    pending_source = await _seed_source(
        container,
        status=SourceStatus.PENDING_REVIEW,
        is_active=True,
    )
    pending_article = await _seed_article(
        container,
        pending_source,
        status=ArticleStatus.NEW,
    )

    inactive_source = await _seed_source(
        container,
        status=SourceStatus.VERIFIED,
        is_active=False,
    )
    inactive_article = await _seed_article(
        container,
        inactive_source,
        status=ArticleStatus.NEW,
    )

    assert (
        await container.article_repository.get_public_article(visible_article.id)
        is not None
    )
    assert (
        await container.article_repository.get_public_article(failed_article.id)
        is None
    )
    assert (
        await container.article_repository.get_public_article(pending_article.id)
        is None
    )
    assert (
        await container.article_repository.get_public_article(inactive_article.id)
        is None
    )

    listed = await container.article_repository.list_public_articles()
    listed_ids = {item.id for item in listed}
    assert visible_article.id in listed_ids
    assert failed_article.id not in listed_ids
    assert pending_article.id not in listed_ids
    assert inactive_article.id not in listed_ids


@pytest.mark.asyncio
async def test_public_visibility_filtering_and_pagination(
    db_session: AsyncSession,
) -> None:
    container = Container(db_session)

    source = await _seed_source(
        container,
        status=SourceStatus.VERIFIED,
        is_active=True,
    )
    base_time = datetime.now(UTC)
    articles = [
        await _seed_article(
            container,
            source,
            status=ArticleStatus.NEW,
            title="needle article" if index == 0 else f"other article {index}",
            published_at=base_time + timedelta(minutes=index),
            importance_score=float(index),
        )
        for index in range(4)
    ]

    search_list = await container.article_repository.list_public_articles(search="needle")
    search_count = await container.article_repository.count_public_articles(search="needle")
    assert len(search_list) == search_count == 1
    assert search_list[0].id == articles[0].id

    min_importance_list = await container.article_repository.list_public_articles(
        min_importance=2.0,
    )
    min_importance_count = await container.article_repository.count_public_articles(
        min_importance=2.0,
    )
    assert len(min_importance_list) == min_importance_count == 2

    published_from = base_time + timedelta(minutes=2)
    date_list = await container.article_repository.list_public_articles(
        published_from=published_from,
    )
    date_count = await container.article_repository.count_public_articles(
        published_from=published_from,
    )
    assert len(date_list) == date_count == 2

    first_page = await container.article_repository.list_public_articles(limit=2, offset=0)
    second_page = await container.article_repository.list_public_articles(limit=2, offset=2)
    assert len(first_page) == 2
    assert len(second_page) == 2
    assert {item.id for item in first_page}.isdisjoint(
        {item.id for item in second_page},
    )

    ordered = await container.article_repository.list_public_articles(order_by="importance")
    assert [item.importance_score for item in ordered] == sorted(
        (item.importance_score for item in ordered),
        reverse=True,
    )
    total_count = await container.article_repository.count_public_articles()
    assert total_count == 4
    assert len(await container.article_repository.list_public_articles()) == total_count
