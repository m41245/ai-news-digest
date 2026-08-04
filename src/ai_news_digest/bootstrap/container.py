from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from ai_news_digest.application.use_cases.article.ingest_all_sources import (
    IngestAllSourcesUseCase,
)
from ai_news_digest.application.use_cases.article.ingest_from_source import (
    IngestFromSourceUseCase,
)
from ai_news_digest.domain.ports.article_repository import ArticleRepository
from ai_news_digest.domain.ports.source_repository import SourceRepository
from ai_news_digest.infrastructure.database.repositories.article_repository import (
    ArticleRepository as SqlAlchemyArticleRepository,
)
from ai_news_digest.infrastructure.database.repositories.source_repository import (
    SourceRepository as SqlAlchemySourceRepository,
)
from ai_news_digest.infrastructure.rss.feedparser_fetcher import (
    FeedparserFetcher,
)


class Container:
    """
    Composition root for the application.

    Responsible for wiring repositories, infrastructure and use cases.
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session = session

    #
    # Repositories
    #

    @property
    def article_repository(self) -> ArticleRepository:
        return SqlAlchemyArticleRepository(self._session)

    @property
    def source_repository(self) -> SourceRepository:
        return SqlAlchemySourceRepository(self._session)

    #
    # Infrastructure
    #

    @property
    def rss_fetcher(self) -> FeedparserFetcher:
        return FeedparserFetcher()

    #
    # Use Cases
    #

    @property
    def ingest_from_source(self) -> IngestFromSourceUseCase:
        return IngestFromSourceUseCase(
            rss_fetcher=self.rss_fetcher,
            article_repository=self.article_repository,
        )

    @property
    def ingest_all_sources(self) -> IngestAllSourcesUseCase:
        return IngestAllSourcesUseCase(
            source_repository=self.source_repository,
            ingest_from_source=self.ingest_from_source,
        )
