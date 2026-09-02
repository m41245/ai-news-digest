"""
True end-to-end pipeline tests for the AI News Digest application.

These tests exercise the *actual application wiring* -- real repositories,
real use cases, real RSS fetcher, real renderers -- rather than only the HTTP
API layer.  External boundaries are mocked where required:

* HTTP downloads from RSS feeds are intercepted via ``httpx.MockTransport``
  so no real network is needed (SSRF validation still runs on the URL).
* AI provider calls are intercepted with a fake ``AIProvider`` implementation
  so no paid/secret API keys are required.
* SMTP delivery is intercepted with a fake ``EmailSender``.

The database is a real PostgreSQL testcontainer (skipped when Docker is
unavailable).
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import override

import httpx
import pytest
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from ai_news_digest.application.ai.config import ProviderConfig
from ai_news_digest.application.ai.decision_engine import DecisionEngine
from ai_news_digest.application.ai.models import AIRequest, AIResponse, AIUsage
from ai_news_digest.application.ai.provider_registry import ProviderRegistry
from ai_news_digest.application.ai.providers.base import AIProvider
from ai_news_digest.bootstrap.container import Container
from ai_news_digest.domain.enums.article_status import ArticleStatus
from ai_news_digest.domain.enums.delivery_status import DeliveryStatus
from ai_news_digest.domain.enums.digest_format import DigestFormat
from ai_news_digest.domain.models.source import Source
from ai_news_digest.domain.ports.email_sender import EmailSender
from ai_news_digest.infrastructure.database.base import Base
from ai_news_digest.infrastructure.database.models import (  # noqa: F401
    article_model,
    category_model,
    digest_article_model,
    digest_delivery_model,
    digest_model,
    source_model,
    user_model,
)
from ai_news_digest.infrastructure.rss.feedparser_fetcher import FeedparserFetcher

# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


class FakeAIProvider(AIProvider):
    """Deterministic AI provider that returns canned responses."""

    def __init__(self) -> None:
        self._config = ProviderConfig(
            provider_name="fake",
            api_key="fake-key",
            enabled=True,
            priority=1,
            model="fake-model",
        )

    @property
    def id(self) -> str:
        return "fake"

    @property
    def name(self) -> str:
        return "FakeAI"

    @property
    def version(self) -> str:
        return "test"

    @property
    def description(self) -> str:
        return "Test AI provider"

    @property
    def capabilities(self) -> set[str]:
        return {"summarization", "categorization"}

    @property
    def enabled(self) -> bool:
        return self._config.enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._config.enabled = value

    def initialize(self) -> None:
        pass

    async def shutdown(self) -> None:
        pass

    async def health_check(self) -> bool:
        return True

    async def available(self) -> bool:
        return True

    def priority(self) -> int:
        return self._config.priority

    @property
    def provider_name(self) -> str:
        return self._config.provider_name

    @property
    def model_name(self) -> str:
        return self._config.model or "fake-model"

    @property
    def supports_streaming(self) -> bool:
        return False

    @property
    def supports_json_mode(self) -> bool:
        return False

    @property
    def supports_vision(self) -> bool:
        return False

    @property
    def max_context_tokens(self) -> int:
        return 4000

    async def generate(self, request: AIRequest) -> AIResponse:
        if "summarizer" in request.system_prompt.lower():
            content = "SUMMARY: A concise summary of the test article."
        elif "classifier" in request.system_prompt.lower():
            content = "AI_RESEARCH"
        else:
            content = "generic-response"
        return AIResponse(
            provider=self.id,
            model=self.model_name,
            content=content,
            usage=AIUsage(),
            latency_ms=1.0,
        )


class FakeEmailSender(EmailSender):
    """In-memory email sender that records sends."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    @override
    async def send(
        self,
        *,
        recipient: str,
        subject: str,
        html: str,
        text: str | None = None,
    ) -> None:
        self.sent.append((recipient, subject))

    @override
    async def send_email(
        self,
        *,
        to: list[str],
        subject: str,
        html_body: str,
        text_body: str | None = None,
    ) -> None:
        self.sent.extend((recipient, subject) for recipient in to)


# ---------------------------------------------------------------------------
# Helper: build a test feed body (RSS 2.0)
# ---------------------------------------------------------------------------

_RSS_TEMPLATE = """\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <title>Test Feed</title>
  <link>https://example.com/</link>
  <description>Test RSS feed for pipeline tests</description>
  {items}
</channel>
</rss>
"""

_ITEM_TEMPLATE = """\
  <item>
    <title>{title}</title>
    <link>{link}</link>
    <description>{summary}</description>
    <pubDate>{pub_date}</pubDate>
    <guid>{guid}</guid>
  </item>
"""


def _build_rss_feed(items: list[tuple[str, str, str]]) -> bytes:
    """Build an RSS 2.0 XML body.

    Each item is (title, link, summary).
    """
    items_xml = "\n".join(
        _ITEM_TEMPLATE.format(
            title=title,
            link=link,
            summary=summary,
            pub_date="Mon, 01 Jan 2024 12:00:00 GMT",
            guid=link,
        )
        for title, link, summary in items
    )
    return _RSS_TEMPLATE.format(items=items_xml).encode("utf-8")


_TEST_FEED_BODY = _build_rss_feed(
    [
        ("AI Breakthrough in Research", "https://example.com/article-1", "Summary 1"),
        ("New AI Model Released", "https://example.com/article-2", "Summary 2"),
        ("AI Product Launches", "https://example.com/article-3", "Summary 3"),
    ]
)


def _make_http_mock_transport(feed_body: bytes = _TEST_FEED_BODY):
    """Create an httpx transport that returns *feed_body* for any request."""

    def _handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            content=feed_body,
            headers={"content-type": "application/xml"},
            request=request,
        )

    return httpx.MockTransport(_handler)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def test_feed_body() -> bytes:
    """Return the test RSS feed body."""
    return _TEST_FEED_BODY


@pytest.fixture
def fake_provider() -> FakeAIProvider:
    """Provide a shared FakeAIProvider instance."""
    return FakeAIProvider()


@pytest.fixture
def fake_email_sender() -> FakeEmailSender:
    """Provide a shared FakeEmailSender instance."""
    return FakeEmailSender()


@pytest.fixture
async def e2e_container(
    postgres_container,
    fake_provider: FakeAIProvider,
    fake_email_sender: FakeEmailSender,
) -> AsyncGenerator[Container, None]:
    """Create a Container wired to the test database with mocked AI/email.

    The Container's internal provider/capability registries are replaced so
    that the *fake* AI provider is used instead of real OpenAI/Anthropic
    clients.
    """
    connection_url = postgres_container.get_connection_url(driver="asyncpg")
    db_url = connection_url.replace("postgresql://", "postgresql+asyncpg://")

    test_engine = create_async_engine(db_url, echo=False, future=True)
    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        container = Container(session)

        # Replace the AI provider registry with one containing the fake provider
        container._provider_registry = ProviderRegistry()
        container._provider_registry.register(fake_provider)
        container._capability_registry.register_provider("summarization", fake_provider.id)
        container._capability_registry.register_provider("categorization", fake_provider.id)
        container._decision_engine = DecisionEngine(
            container._provider_registry,
            container._capability_registry,
        )

        # Store the fake email sender on the instance so tests can access it
        container.__dict__["_test_email_sender"] = fake_email_sender

        yield container

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


# ---------------------------------------------------------------------------
# Pipeline test: RSS -> ingestion -> processing -> digest -> rendering -> delivery
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestE2EPipeline:
    """Full pipeline test exercising real application wiring."""

    async def test_full_pipeline_rss_to_email_delivery(
        self,
        e2e_container: Container,
        fake_provider: FakeAIProvider,
        fake_email_sender: FakeEmailSender,
        test_feed_body: bytes,
    ) -> None:
        """Exercise the complete pipeline: fetch -> ingest -> process -> digest -> render -> email.

        Steps:
        1. Create a source with a mock transport feed
        2. Ingest articles from the source (real IngestFromSourceUseCase)
        3. Verify articles are persisted with NEW status
        4. Process articles through AI summarization + categorization
        5. Verify articles transition to CATEGORIZED status
        6. Generate a digest from eligible articles
        7. Render the digest as Markdown and HTML
        8. Deliver the digest via email (mocked)
        9. Verify delivery records and email sends
        """
        # --- Step 1: Create a source ---
        source = Source.create(
            name="E2E Pipeline Source",
            feed_url="https://example.com/feed.xml",
            website_url="https://example.com",
            description="Source for E2E pipeline test",
        )
        source = await e2e_container.source_repository.create(source)

        # --- Step 2: Ingest articles using a real fetcher with mocked HTTP ---
        fetcher = FeedparserFetcher(
            timeout=5.0,
            max_articles=50,
            max_response_bytes=1024 * 1024,
            transport=_make_http_mock_transport(test_feed_body),
        )

        ingest_uc = e2e_container.ingest_from_source
        ingest_uc._rss_fetcher = fetcher  # type: ignore[assignment]

        result = await ingest_uc.execute(source)

        # --- Step 3: Verify ingestion results ---
        assert result.fetched == 3
        assert result.imported == 3
        assert result.skipped == 0
        assert result.failed == 0

        # Verify articles were persisted
        articles = await e2e_container.article_repository.list_recent(limit=10)
        source_articles = [a for a in articles if a.source_id == source.id]
        assert len(source_articles) == 3
        for article in source_articles:
            assert article.status == ArticleStatus.NEW
            assert article.summary != ""
            assert article.published_at.year == 2024

        # --- Step 4: Process each article (summarize + categorize) ---
        process_uc = e2e_container.process_article

        for article in source_articles:
            updated_article = await process_uc.execute(article)
            assert updated_article.status == ArticleStatus.CATEGORIZED
            assert updated_article.summary.startswith("SUMMARY:")
            assert updated_article.category_id is not None

        # --- Step 5: Verify articles are digest-eligible ---
        eligible = await e2e_container.article_repository.list_digest_eligible()
        eligible_from_source = [a for a in eligible if a.source_id == source.id]
        assert len(eligible_from_source) == 3
        for article in eligible_from_source:
            assert article.status in (ArticleStatus.SUMMARIZED, ArticleStatus.CATEGORIZED)
            assert article.category_id is not None

        # --- Step 6: Generate a digest ---
        digest_uc = e2e_container.generate_digest
        digest_result = await digest_uc.execute(title="Test Pipeline Digest")

        assert digest_result.included_articles == 3
        assert digest_result.digest_id is not None

        # Verify digest was persisted
        persisted_digest = await e2e_container.digest_repository.get_by_id(digest_result.digest_id)
        assert persisted_digest is not None
        assert persisted_digest.title == "Test Pipeline Digest"
        assert len(persisted_digest.article_ids) == 3

        # --- Step 7: Render the digest as Markdown and HTML ---
        renderer_factory = e2e_container.rendering_factory

        md_rendered = renderer_factory.get_renderer(DigestFormat.MARKDOWN).render(persisted_digest)
        assert md_rendered.format == DigestFormat.MARKDOWN
        assert "Test Pipeline Digest" in md_rendered.content
        assert "SUMMARY:" in md_rendered.content

        html_rendered = renderer_factory.get_renderer(DigestFormat.HTML).render(persisted_digest)
        assert html_rendered.format == DigestFormat.HTML
        assert "<h1>Test Pipeline Digest</h1>" in html_rendered.content

        # --- Step 8: Deliver the digest via email ---
        from ai_news_digest.application.use_cases.delivery.deliver_digest import (
            DeliverDigestUseCase,
        )
        from ai_news_digest.infrastructure.email.composer import EmailComposer

        deliver_uc = DeliverDigestUseCase(
            digest_repository=e2e_container.digest_repository,
            delivery_repository=e2e_container.delivery_repository,
            email_sender=fake_email_sender,
            email_composer=EmailComposer(),
            recipients=["test@example.com"],
        )

        delivery_summary = await deliver_uc.execute(digest_result.digest_id)

        assert delivery_summary.total_recipients == 1
        assert delivery_summary.sent_count == 1
        assert delivery_summary.failed_count == 0
        assert len(fake_email_sender.sent) == 1
        assert fake_email_sender.sent[0][0] == "test@example.com"
        assert "Test Pipeline Digest" in fake_email_sender.sent[0][1]

        # --- Step 9: Verify delivery records ---
        deliveries = await e2e_container.delivery_repository.list_by_digest(digest_result.digest_id)
        assert len(deliveries) == 1
        assert deliveries[0].recipient == "test@example.com"
        assert deliveries[0].status == DeliveryStatus.SENT
