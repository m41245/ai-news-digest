from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from ai_news_digest.application.ai.capability import Capability
from ai_news_digest.application.ai.capability_registry import CapabilityRegistry
from ai_news_digest.application.ai.decision_engine import DecisionEngine
from ai_news_digest.application.ai.provider_registry import ProviderRegistry
from ai_news_digest.application.rendering.renderer_factory import (
    DigestRendererFactory,
)
from ai_news_digest.application.use_cases.article.categorize_article import (
    CategorizeArticleUseCase,
)
from ai_news_digest.application.use_cases.article.ingest_all_sources import (
    IngestAllSourcesUseCase,
)
from ai_news_digest.application.use_cases.article.ingest_from_source import (
    IngestFromSourceUseCase,
)
from ai_news_digest.application.use_cases.article.summarize_article import (
    SummarizeArticleUseCase,
)
from ai_news_digest.application.use_cases.digest.generate_digest import (
    GenerateDigestUseCase,
)
from ai_news_digest.domain.ports.article_repository import ArticleRepository
from ai_news_digest.domain.ports.digest_repository import (
    DigestRepository as DigestRepositoryPort,
)
from ai_news_digest.domain.ports.source_repository import SourceRepository
from ai_news_digest.infrastructure.database.repositories.article_repository import (
    ArticleRepository as SqlAlchemyArticleRepository,
)
from ai_news_digest.infrastructure.database.repositories.digest_repository import (
    DigestRepository as SqlAlchemyDigestRepository,
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

    Responsible for wiring repositories, infrastructure, registry services and
    use cases.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._provider_registry = ProviderRegistry()
        self._capability_registry = CapabilityRegistry()
        self._configure_capabilities()
        self._decision_engine = DecisionEngine(
            self._provider_registry,
            self._capability_registry,
        )

    def _configure_capabilities(self) -> None:
        """Register the platform capabilities supported by providers."""
        self._capability_registry.register_capability(
            Capability(
                id="summarization",
                name="Summarization",
                description="Summarize article text into a concise digestible summary.",
                category="content",
            )
        )
        self._capability_registry.register_capability(
            Capability(
                id="categorization",
                name="Categorization",
                description="Classify article content into a topical category.",
                category="classification",
            )
        )

    #
    # Repositories
    #

    @property
    def article_repository(self) -> ArticleRepository:
        return SqlAlchemyArticleRepository(self._session)

    @property
    def source_repository(self) -> SourceRepository:
        return SqlAlchemySourceRepository(self._session)

    @property
    def digest_repository(self) -> DigestRepositoryPort:
        return SqlAlchemyDigestRepository(self._session)

    #
    # Infrastructure
    #

    @property
    def rss_fetcher(self) -> FeedparserFetcher:
        return FeedparserFetcher()

    @property
    def provider_registry(self) -> ProviderRegistry:
        return self._provider_registry

    @property
    def capability_registry(self) -> CapabilityRegistry:
        return self._capability_registry

    @property
    def decision_engine(self) -> DecisionEngine:
        return self._decision_engine

    @property
    def rendering_factory(self) -> DigestRendererFactory:
        return DigestRendererFactory()

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

    @property
    def summarize_article(self) -> SummarizeArticleUseCase:
        return SummarizeArticleUseCase(
            decision_engine=self.decision_engine,
            provider_registry=self.provider_registry,
            article_repository=self.article_repository,
        )

    @property
    def categorize_article(self) -> CategorizeArticleUseCase:
        return CategorizeArticleUseCase(
            decision_engine=self.decision_engine,
            provider_registry=self.provider_registry,
            article_repository=self.article_repository,
        )

    @property
    def generate_digest(self) -> GenerateDigestUseCase:
        return GenerateDigestUseCase(
            article_repository=self.article_repository,
            digest_repository=self.digest_repository,
        )


__all__ = ["Container"]
