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
from ai_news_digest.application.use_cases.article.analyze_and_materialize import (
    AnalyzeAndMaterializeUseCase,
)
from ai_news_digest.application.use_cases.article.analyze_article import (
    AnalyzeArticleUseCase,
    get_provider_priority_provider_id,
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
from ai_news_digest.application.use_cases.article.extract_article import (
    ExtractArticleUseCase,
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
from ai_news_digest.application.use_cases.story_cluster.cluster_articles import (
    ClusterArticlesUseCase,
)
from ai_news_digest.application.use_cases.story_cluster.create_story_cluster import (
    CreateStoryClusterUseCase,
)
from ai_news_digest.application.use_cases.story_cluster.get_story_cluster import (
    GetStoryClusterUseCase,
)
from ai_news_digest.application.use_cases.story_cluster.list_story_clusters import (
    ListStoryClustersUseCase,
)
from ai_news_digest.application.use_cases.user_preference.follow_category import (
    FollowCategoryUseCase,
)
from ai_news_digest.application.use_cases.user_preference.follow_company import (
    FollowCompanyUseCase,
)
from ai_news_digest.application.use_cases.user_preference.follow_topic import (
    FollowTopicUseCase,
)
from ai_news_digest.application.use_cases.user_preference.get_personalized_feed import (
    GetPersonalizedFeedUseCase,
)
from ai_news_digest.application.use_cases.user_preference.get_preferences import (
    GetPreferencesUseCase,
)
from ai_news_digest.application.use_cases.user_preference.mute_category import (
    MuteCategoryUseCase,
)
from ai_news_digest.application.use_cases.user_preference.mute_company import (
    MuteCompanyUseCase,
)
from ai_news_digest.application.use_cases.user_preference.mute_topic import (
    MuteTopicUseCase,
)
from ai_news_digest.application.use_cases.user_preference.reset_preferences import (
    ResetPreferencesUseCase,
)
from ai_news_digest.application.use_cases.user_preference.unfollow_category import (
    UnfollowCategoryUseCase,
)
from ai_news_digest.application.use_cases.user_preference.unfollow_company import (
    UnfollowCompanyUseCase,
)
from ai_news_digest.application.use_cases.user_preference.unfollow_topic import (
    UnfollowTopicUseCase,
)
from ai_news_digest.application.use_cases.user_preference.unmute_category import (
    UnmuteCategoryUseCase,
)
from ai_news_digest.application.use_cases.user_preference.unmute_company import (
    UnmuteCompanyUseCase,
)
from ai_news_digest.application.use_cases.user_preference.unmute_topic import (
    UnmuteTopicUseCase,
)
from ai_news_digest.application.use_cases.user_preference.update_preferences import (
    UpdatePreferencesUseCase,
)
from ai_news_digest.core.config import get_settings
from ai_news_digest.domain.models.url import CanonicalUrl
from ai_news_digest.domain.ports.article_repository import ArticleRepository
from ai_news_digest.domain.ports.cache_store import CacheStore
from ai_news_digest.domain.ports.category_repository import CategoryRepository
from ai_news_digest.domain.ports.company_repository import CompanyRepository
from ai_news_digest.domain.ports.delivery_repository import DeliveryRepository
from ai_news_digest.domain.ports.digest_repository import (
    DigestRepository as DigestRepositoryPort,
)
from ai_news_digest.domain.ports.email_sender import EmailSender
from ai_news_digest.domain.ports.notification_repository import (
    NotificationDeliveryRepository,
    NotificationPreferenceRepository,
    NotificationRepository,
)
from ai_news_digest.domain.ports.source_repository import SourceRepository
from ai_news_digest.domain.ports.story_cluster_repository import StoryClusterRepository
from ai_news_digest.domain.ports.topic_repository import TopicRepository
from ai_news_digest.domain.ports.user_preference_repository import UserPreferenceRepository
from ai_news_digest.domain.ports.user_repository import UserRepository
from ai_news_digest.infrastructure.cache.redis_store import RedisStore
from ai_news_digest.infrastructure.database.repositories.article_repository import (
    ArticleRepository as SqlAlchemyArticleRepository,
)
from ai_news_digest.infrastructure.database.repositories.category_repository import (
    CategoryRepository as SqlAlchemyCategoryRepository,
)
from ai_news_digest.infrastructure.database.repositories.company_repository import (
    SqlAlchemyCompanyRepository,
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
from ai_news_digest.infrastructure.database.repositories.story_cluster_repository import (
    StoryClusterRepository as SqlAlchemyStoryClusterRepository,
)
from ai_news_digest.infrastructure.database.repositories.topic_repository import (
    SqlAlchemyTopicRepository,
)
from ai_news_digest.infrastructure.database.repositories.user_preference_repository import (
    UserPreferenceRepository as SqlAlchemyUserPreferenceRepository,
)
from ai_news_digest.infrastructure.database.repositories.user_repository import (
    UserRepository as SqlAlchemyUserRepository,
)
from ai_news_digest.infrastructure.email.composer import EmailComposer
from ai_news_digest.infrastructure.extraction.content_cleaner import ContentCleaner
from ai_news_digest.infrastructure.extraction.ssrf_http_client import (
    SsrfHttpArticleFetcher,
)
from ai_news_digest.infrastructure.extraction.stdlib_extractor import (
    StdlibHtmlExtractor,
)
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

    @property
    def session(self) -> AsyncSession:
        """Return the underlying database session for infrastructure queries."""
        return self._session

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
    def company_repository(self) -> CompanyRepository:
        return SqlAlchemyCompanyRepository(self._session)

    @property
    def topic_repository(self) -> TopicRepository:
        return SqlAlchemyTopicRepository(self._session)

    @property
    def story_cluster_repository(self) -> StoryClusterRepository:
        return SqlAlchemyStoryClusterRepository(self._session)

    @property
    def user_repository(self) -> UserRepository:
        return SqlAlchemyUserRepository(self._session)

    @property
    def user_preference_repository(self) -> UserPreferenceRepository:
        return SqlAlchemyUserPreferenceRepository(self._session)

    #
    # Infrastructure
    #

    @property
    def rss_fetcher(self) -> FeedparserFetcher:
        return FeedparserFetcher(
            timeout=self._settings.rss_request_timeout,
            max_articles=self._settings.rss_max_articles_per_feed,
            max_response_bytes=self._settings.rss_max_response_bytes,
        )

    @property
    def article_fetcher(self) -> SsrfHttpArticleFetcher:
        return SsrfHttpArticleFetcher(
            max_response_bytes=self._settings.rss_max_response_bytes,
        )

    @property
    def html_extractor(self) -> StdlibHtmlExtractor:
        return StdlibHtmlExtractor()

    @property
    def content_cleaner(self) -> ContentCleaner:
        return ContentCleaner()

    @property
    def canonical_url(self) -> type[CanonicalUrl]:
        return CanonicalUrl

    @property
    def cache_store(self) -> CacheStore:
        return RedisStore(self._settings.redis_url)

    @property
    def email_sender(self) -> EmailSender:
        from ai_news_digest.infrastructure.email.provider_factory import create_email_sender

        return create_email_sender(self._settings)

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
    def extract_article(self) -> ExtractArticleUseCase:
        return ExtractArticleUseCase(
            article_fetcher=self.article_fetcher,
            html_extractor=self.html_extractor,
            content_cleaner=self.content_cleaner,
            article_repository=self.article_repository,
        )

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
    def analyze_article(self) -> AnalyzeArticleUseCase | None:
        provider_id = get_provider_priority_provider_id(self.provider_registry)
        if provider_id is None:
            return None
        return AnalyzeArticleUseCase(
            provider_registry=self.provider_registry,
            provider_id=provider_id,
        )

    @property
    def analyze_and_materialize(self) -> AnalyzeAndMaterializeUseCase | None:
        analyze_use_case = self.analyze_article
        if analyze_use_case is None:
            return None
        return AnalyzeAndMaterializeUseCase(
            analyze_use_case=analyze_use_case,
            article_repository=self.article_repository,
            company_repository=self.company_repository,
            topic_repository=self.topic_repository,
            category_repository=self.category_repository,
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

    @property
    def cluster_articles(self) -> ClusterArticlesUseCase:
        return ClusterArticlesUseCase(
            article_repository=self.article_repository,
            cluster_repository=self.story_cluster_repository,
        )

    @property
    def create_story_cluster(self) -> CreateStoryClusterUseCase:
        return CreateStoryClusterUseCase(
            repository=self.story_cluster_repository,
        )

    @property
    def get_story_cluster(self) -> GetStoryClusterUseCase:
        return GetStoryClusterUseCase(
            cluster_repository=self.story_cluster_repository,
            article_repository=self.article_repository,
            source_repository=self.source_repository,
        )

    @property
    def list_story_clusters(self) -> ListStoryClustersUseCase:
        return ListStoryClustersUseCase(
            repository=self.story_cluster_repository,
        )

    @property
    def get_preferences(self) -> GetPreferencesUseCase:
        return GetPreferencesUseCase(
            preference_repository=self.user_preference_repository,
        )

    @property
    def update_preferences(self) -> UpdatePreferencesUseCase:
        return UpdatePreferencesUseCase(
            preference_repository=self.user_preference_repository,
        )

    @property
    def reset_preferences(self) -> ResetPreferencesUseCase:
        return ResetPreferencesUseCase(
            preference_repository=self.user_preference_repository,
        )

    @property
    def follow_company(self) -> FollowCompanyUseCase:
        return FollowCompanyUseCase(
            preference_repository=self.user_preference_repository,
        )

    @property
    def unfollow_company(self) -> UnfollowCompanyUseCase:
        return UnfollowCompanyUseCase(
            preference_repository=self.user_preference_repository,
        )

    @property
    def follow_topic(self) -> FollowTopicUseCase:
        return FollowTopicUseCase(
            preference_repository=self.user_preference_repository,
        )

    @property
    def unfollow_topic(self) -> UnfollowTopicUseCase:
        return UnfollowTopicUseCase(
            preference_repository=self.user_preference_repository,
        )

    @property
    def follow_category(self) -> FollowCategoryUseCase:
        return FollowCategoryUseCase(
            preference_repository=self.user_preference_repository,
        )

    @property
    def unfollow_category(self) -> UnfollowCategoryUseCase:
        return UnfollowCategoryUseCase(
            preference_repository=self.user_preference_repository,
        )

    @property
    def mute_company(self) -> MuteCompanyUseCase:
        return MuteCompanyUseCase(
            preference_repository=self.user_preference_repository,
        )

    @property
    def unmute_company(self) -> UnmuteCompanyUseCase:
        return UnmuteCompanyUseCase(
            preference_repository=self.user_preference_repository,
        )

    @property
    def mute_topic(self) -> MuteTopicUseCase:
        return MuteTopicUseCase(
            preference_repository=self.user_preference_repository,
        )

    @property
    def unmute_topic(self) -> UnmuteTopicUseCase:
        return UnmuteTopicUseCase(
            preference_repository=self.user_preference_repository,
        )

    @property
    def mute_category(self) -> MuteCategoryUseCase:
        return MuteCategoryUseCase(
            preference_repository=self.user_preference_repository,
        )

    @property
    def unmute_category(self) -> UnmuteCategoryUseCase:
        return UnmuteCategoryUseCase(
            preference_repository=self.user_preference_repository,
        )

    @property
    def get_personalized_feed(self) -> GetPersonalizedFeedUseCase:
        return GetPersonalizedFeedUseCase(
            preference_repository=self.user_preference_repository,
            article_repository=self.article_repository,
            story_cluster_repository=self.story_cluster_repository,
            source_repository=self.source_repository,
            category_repository=self.category_repository,
            company_repository=self.company_repository,
        )

    @property
    def notification_repository(self) -> NotificationRepository:
        from ai_news_digest.infrastructure.database.repositories.notification_repository import (
            NotificationRepository as SqlAlchemyNotificationRepository,
        )

        return SqlAlchemyNotificationRepository(self._session)

    @property
    def notification_delivery_repository(self) -> NotificationDeliveryRepository:
        from ai_news_digest.infrastructure.database.repositories.notification_repository import (
            NotificationDeliveryRepository as SqlAlchemyNotificationDeliveryRepository,
        )

        return SqlAlchemyNotificationDeliveryRepository(self._session)

    @property
    def notification_preference_repository(self) -> NotificationPreferenceRepository:
        from ai_news_digest.infrastructure.database.repositories.notification_repository import (
            NotificationPreferenceRepository as SqlAlchemyNotificationPreferenceRepository,
        )

        return SqlAlchemyNotificationPreferenceRepository(self._session)

    @property
    def notification_eligibility_engine(self) -> NotificationEligibilityEngine:  # type: ignore[name-defined] # noqa: F821
        from ai_news_digest.application.services.notifications.eligibility_engine import (
            NotificationEligibilityEngine,
        )

        return NotificationEligibilityEngine(
            notification_repository=self.notification_repository,
            notification_preference_repo=self.notification_preference_repository,
            user_preference_repo=self.user_preference_repository,
        )

    @property
    def notification_service(self) -> NotificationService:  # type: ignore[name-defined] # noqa: F821
        from ai_news_digest.application.services.notifications.notification_service import (
            NotificationService,
        )
        from ai_news_digest.infrastructure.email.notification_composer import (
            NotificationEmailComposer,
        )

        return NotificationService(
            notification_repository=self.notification_repository,
            delivery_repository=self.notification_delivery_repository,
            preference_repository=self.notification_preference_repository,
            eligibility_engine=self.notification_eligibility_engine,
            email_composer=NotificationEmailComposer(),
        )

    @property
    def notification_scheduling_service(self):
        from ai_news_digest.application.services.notifications.scheduling_service import (
            NotificationSchedulingService,
        )

        return NotificationSchedulingService(
            notification_repo=self.notification_repository,
            delivery_repo=self.notification_delivery_repository,
            preference_repo=self.notification_preference_repository,
        )

    @property
    def notification_rate_limiter(self):
        from ai_news_digest.application.services.notifications.rate_limiter import (
            NotificationRateLimiter,
        )

        return NotificationRateLimiter(
            delivery_repo=self.notification_delivery_repository,
        )

    @property
    def notification_delivery_service(self):
        from ai_news_digest.application.services.notifications.delivery_service import (
            NotificationDeliveryService,
        )

        return NotificationDeliveryService(
            delivery_repo=self.notification_delivery_repository,
            notification_repo=self.notification_repository,
            user_repo=self.user_repository,
        )

    @property
    def digest_batching_service(self):
        from ai_news_digest.application.services.notifications.digest_batching_service import (
            DigestBatchingService,
        )

        return DigestBatchingService(
            notification_repo=self.notification_repository,
            delivery_repo=self.notification_delivery_repository,
            preference_repo=self.notification_preference_repository,
        )


__all__ = ["Container"]
