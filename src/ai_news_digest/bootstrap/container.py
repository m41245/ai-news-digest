from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from ai_news_digest.application.ai.capability import Capability
from ai_news_digest.application.ai.capability_registry import CapabilityRegistry
from ai_news_digest.application.ai.config import ProviderConfig
from ai_news_digest.application.ai.decision_engine import DecisionEngine
from ai_news_digest.application.ai.provider_registry import ProviderRegistry
from ai_news_digest.application.rendering.renderer_factory import (
    DigestRendererFactory,
)
from ai_news_digest.application.use_cases.article.categorize_article import (
    CategorizeArticleUseCase,
)
from ai_news_digest.application.use_cases.article.create import (
    CreateArticleUseCase,
)
from ai_news_digest.application.use_cases.article.delete import (
    DeleteArticleUseCase,
)
from ai_news_digest.application.use_cases.article.get import (
    GetArticleUseCase,
)
from ai_news_digest.application.use_cases.article.ingest_all_sources import (
    IngestAllSourcesUseCase,
)
from ai_news_digest.application.use_cases.article.ingest_from_source import (
    IngestFromSourceUseCase,
)
from ai_news_digest.application.use_cases.article.list import (
    ListArticlesUseCase,
)
from ai_news_digest.application.use_cases.article.process_article import (
    ProcessArticleUseCase,
)
from ai_news_digest.application.use_cases.article.summarize_article import (
    SummarizeArticleUseCase,
)
from ai_news_digest.application.use_cases.article.update import (
    UpdateArticleUseCase,
)
from ai_news_digest.application.use_cases.category.update import (
    UpdateCategoryUseCase,
)
from ai_news_digest.application.use_cases.delivery.deliver_digest import (
    DeliverDigestUseCase,
)
from ai_news_digest.application.use_cases.digest.generate_digest import (
    GenerateDigestUseCase,
)
from ai_news_digest.application.use_cases.digest.update import (
    UpdateDigestUseCase,
)
from ai_news_digest.application.use_cases.source.update import (
    UpdateSourceUseCase,
)
from ai_news_digest.core.config import get_settings
from ai_news_digest.domain.models.url import CanonicalUrl
from ai_news_digest.domain.ports.article_repository import ArticleRepository
from ai_news_digest.domain.ports.cache_store import CacheStore
from ai_news_digest.domain.ports.category_repository import CategoryRepository
from ai_news_digest.domain.ports.delivery_repository import DeliveryRepository
from ai_news_digest.domain.ports.digest_repository import (
    DigestRepository as DigestRepositoryPort,
)
from ai_news_digest.domain.ports.email_sender import EmailSender
from ai_news_digest.domain.ports.source_repository import SourceRepository
from ai_news_digest.domain.ports.user_repository import UserRepository
from ai_news_digest.infrastructure.cache.redis_store import RedisStore
from ai_news_digest.infrastructure.database.repositories.article_repository import (
    ArticleRepository as SqlAlchemyArticleRepository,
)
from ai_news_digest.infrastructure.database.repositories.category_repository import (
    CategoryRepository as SqlAlchemyCategoryRepository,
)
from ai_news_digest.infrastructure.database.repositories.delivery_repository import (
    DeliveryRepository as SqlAlchemyDeliveryRepository,
)
from ai_news_digest.infrastructure.database.repositories.digest_repository import (
    DigestRepository as SqlAlchemyDigestRepository,
)
from ai_news_digest.infrastructure.database.repositories.source_repository import (
    SourceRepository as SqlAlchemySourceRepository,
)
from ai_news_digest.infrastructure.database.repositories.user_repository import (
    UserRepository as SqlAlchemyUserRepository,
)
from ai_news_digest.infrastructure.email.composer import EmailComposer
from ai_news_digest.infrastructure.email.smtp_sender import SMTPSender
from ai_news_digest.infrastructure.llm.factory import LLMProviderFactory
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
        self._settings = get_settings()
        self._provider_registry = ProviderRegistry()
        self._capability_registry = CapabilityRegistry()
        self._configure_capabilities()
        self._configure_providers()
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

    def _configure_providers(self) -> None:
        """Configure and register AI providers."""
        if self._settings.openai_enabled and self._settings.openai_api_key:
            openai_config = ProviderConfig(
                provider_name="openai",
                api_key=self._settings.openai_api_key.get_secret_value(),
                enabled=self._settings.openai_enabled,
                priority=self._settings.openai_priority,
                model=self._settings.openai_model,
                timeout=self._settings.openai_timeout,
                max_retries=self._settings.openai_max_retries,
            )
            openai_provider = LLMProviderFactory.create_openai_provider(openai_config)
            self._provider_registry.register(openai_provider)
            self._capability_registry.register_provider("summarization", openai_provider.id)
            self._capability_registry.register_provider("categorization", openai_provider.id)

        if self._settings.anthropic_enabled and self._settings.anthropic_api_key:
            anthropic_config = ProviderConfig(
                provider_name="anthropic",
                api_key=self._settings.anthropic_api_key.get_secret_value(),
                enabled=self._settings.anthropic_enabled,
                priority=self._settings.anthropic_priority,
                model=self._settings.anthropic_model,
                timeout=self._settings.anthropic_timeout,
                max_retries=self._settings.anthropic_max_retries,
            )
            anthropic_provider = LLMProviderFactory.create_anthropic_provider(anthropic_config)
            self._provider_registry.register(anthropic_provider)
            self._capability_registry.register_provider("summarization", anthropic_provider.id)
            self._capability_registry.register_provider("categorization", anthropic_provider.id)

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

    @property
    def delivery_repository(self) -> DeliveryRepository:
        return SqlAlchemyDeliveryRepository(self._session)

    @property
    def category_repository(self) -> CategoryRepository:
        return SqlAlchemyCategoryRepository(self._session)

    @property
    def user_repository(self) -> UserRepository:
        return SqlAlchemyUserRepository(self._session)

    #
    # Infrastructure
    #

    @property
    def rss_fetcher(self) -> FeedparserFetcher:
        return FeedparserFetcher(
            timeout=self._settings.rss_request_timeout,
            max_articles=self._settings.rss_max_articles_per_feed,
        )

    @property
    def canonical_url(self) -> type[CanonicalUrl]:
        return CanonicalUrl

    @property
    def cache_store(self) -> CacheStore:
        return RedisStore(self._settings.redis_url)

    @property
    def email_sender(self) -> EmailSender:
        return SMTPSender()

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

    @property
    def email_composer(self) -> EmailComposer:
        return EmailComposer()

    @property
    def deliver_digest(self) -> DeliverDigestUseCase:
        recipients = self._settings.email_recipients
        assert isinstance(recipients, list)  # noqa: S101
        return DeliverDigestUseCase(
            digest_repository=self.digest_repository,
            delivery_repository=self.delivery_repository,
            email_sender=self.email_sender,
            email_composer=self.email_composer,
            recipients=recipients,
        )

    #
    # Use Cases
    #

    @property
    def ingest_from_source(self) -> IngestFromSourceUseCase:
        return IngestFromSourceUseCase(
            rss_fetcher=self.rss_fetcher,
            article_repository=self.article_repository,
            canonical_url=self.canonical_url,
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
            max_content_length=self._settings.ai_max_content_length,
        )

    @property
    def categorize_article(self) -> CategorizeArticleUseCase:
        return CategorizeArticleUseCase(
            decision_engine=self.decision_engine,
            provider_registry=self.provider_registry,
            article_repository=self.article_repository,
            category_repository=self.category_repository,
        )

    @property
    def process_article(self) -> ProcessArticleUseCase:
        return ProcessArticleUseCase(
            summarize_use_case=self.summarize_article,
            categorize_use_case=self.categorize_article,
            article_repository=self.article_repository,
        )

    @property
    def generate_digest(self) -> GenerateDigestUseCase:
        return GenerateDigestUseCase(
            article_repository=self.article_repository,
            digest_repository=self.digest_repository,
            source_repository=self.source_repository,
            category_repository=self.category_repository,
        )

    @property
    def update_source(self) -> UpdateSourceUseCase:
        return UpdateSourceUseCase(
            repository=self.source_repository,
        )

    @property
    def update_article(self) -> UpdateArticleUseCase:
        return UpdateArticleUseCase(
            repository=self.article_repository,
        )

    @property
    def create_article(self) -> CreateArticleUseCase:
        return CreateArticleUseCase(
            repository=self.article_repository,
        )

    @property
    def get_article(self) -> GetArticleUseCase:
        return GetArticleUseCase(
            repository=self.article_repository,
        )

    @property
    def list_articles(self) -> ListArticlesUseCase:
        return ListArticlesUseCase(
            repository=self.article_repository,
        )

    @property
    def delete_article(self) -> DeleteArticleUseCase:
        return DeleteArticleUseCase(
            repository=self.article_repository,
        )

    @property
    def update_category(self) -> UpdateCategoryUseCase:
        return UpdateCategoryUseCase(
            repository=self.category_repository,
        )

    @property
    def update_digest(self) -> UpdateDigestUseCase:
        return UpdateDigestUseCase(
            repository=self.digest_repository,
        )


__all__ = ["Container"]
