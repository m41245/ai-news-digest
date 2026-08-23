"""
Unit tests for Container.
"""

from __future__ import annotations

import pytest
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession

from ai_news_digest.application.ai.models import AIRequest, AIResponse, AIUsage
from ai_news_digest.application.ai.providers.base import AIProvider as RealAIProvider
from ai_news_digest.bootstrap.container import Container


class AIProvider(RealAIProvider):
    """Minimal concrete AIProvider for testing Container wiring."""

    def __init__(self, provider_id: str = "test", provider_name: str = "test") -> None:
        super().__init__()
        self._provider_id = provider_id
        self._provider_name = provider_name

    @property
    def id(self) -> str:
        return self._provider_id

    @property
    def name(self) -> str:
        return self._provider_name

    @property
    def version(self) -> str:
        return "1.0"

    @property
    def description(self) -> str:
        return "test"

    @property
    def capabilities(self) -> set:
        return {"summarization"}

    @property
    def enabled(self) -> bool:
        return True

    def initialize(self) -> None:
        pass

    def shutdown(self) -> None:
        pass

    async def available(self) -> bool:
        return True

    def priority(self) -> int:
        return 1

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def model_name(self) -> str:
        return "gpt-4o-mini"

    @property
    def supports_streaming(self) -> bool:
        return True

    @property
    def supports_json_mode(self) -> bool:
        return True

    @property
    def supports_vision(self) -> bool:
        return False

    @property
    def max_context_tokens(self) -> int:
        return 128000

    async def generate(self, request: AIRequest) -> AIResponse:
        return AIResponse(
            provider=self._provider_name,
            model=self._model_name,
            content="test response",
            usage=AIUsage(),
            latency_ms=0.0,
            metadata=request.metadata if request else {},
        )

    async def health_check(self) -> bool:
        return True


@pytest.fixture
def mock_session() -> AsyncSession:
    """Create a mock AsyncSession."""
    from unittest.mock import MagicMock

    session = MagicMock(spec=AsyncSession)
    return session


@pytest.fixture
def container(mock_session: AsyncSession) -> Container:
    """Create a Container instance with a mock session."""
    return Container(mock_session)


def test_container_initialization(container: Container) -> None:
    """Test Container initialization."""
    assert container._session is not None
    assert container._provider_registry is not None
    assert container._capability_registry is not None
    assert container._decision_engine is not None


def test_container_article_repository(container: Container) -> None:
    """Test article_repository property."""
    repo = container.article_repository
    assert repo is not None
    assert repo._session == container._session


def test_container_source_repository(container: Container) -> None:
    """Test source_repository property."""
    repo = container.source_repository
    assert repo is not None
    assert repo._session == container._session


def test_container_digest_repository(container: Container) -> None:
    """Test digest_repository property."""
    repo = container.digest_repository
    assert repo is not None
    assert repo._session == container._session


def test_container_category_repository(container: Container) -> None:
    """Test category_repository property."""
    repo = container.category_repository
    assert repo is not None
    assert repo._session == container._session


def test_container_rss_fetcher(container: Container) -> None:
    """Test rss_fetcher property."""
    fetcher = container.rss_fetcher
    assert fetcher is not None


def test_container_provider_registry(container: Container) -> None:
    """Test provider_registry property."""
    registry = container.provider_registry
    assert registry is not None
    assert registry == container._provider_registry


def test_container_capability_registry(container: Container) -> None:
    """Test capability_registry property."""
    registry = container.capability_registry
    assert registry is not None
    assert registry == container._capability_registry


def test_container_decision_engine(container: Container) -> None:
    """Test decision_engine property."""
    engine = container.decision_engine
    assert engine is not None
    assert engine == container._decision_engine


def test_container_rendering_factory(container: Container) -> None:
    """Test rendering_factory property."""
    factory = container.rendering_factory
    assert factory is not None


def test_container_cache_store(container: Container) -> None:
    """Test cache_store property."""
    cache = container.cache_store
    assert cache is not None


def test_container_email_sender(container: Container) -> None:
    """Test email_sender property."""
    sender = container.email_sender
    assert sender is not None


def test_container_ingest_from_source(container: Container) -> None:
    """Test ingest_from_source property."""
    use_case = container.ingest_from_source
    assert use_case is not None


def test_container_ingest_all_sources(container: Container) -> None:
    """Test ingest_all_sources property."""
    use_case = container.ingest_all_sources
    assert use_case is not None


def test_container_summarize_article(container: Container) -> None:
    """Test summarize_article property."""
    use_case = container.summarize_article
    assert use_case is not None


def test_container_categorize_article(container: Container) -> None:
    """Test categorize_article property."""
    use_case = container.categorize_article
    assert use_case is not None


def test_container_generate_digest(container: Container) -> None:
    """Test generate_digest property."""
    use_case = container.generate_digest
    assert use_case is not None


def test_container_provider_registration_openai(monkeypatch) -> None:
    """Test that OpenAI provider registration works when an API key is configured."""
    from unittest.mock import MagicMock, patch

    from ai_news_digest.application.ai.config import ProviderConfig

    fake_settings = MagicMock()
    fake_settings.openai_enabled = True
    fake_settings.openai_api_key = SecretStr("test-openai-key")
    fake_settings.openai_priority = 1
    fake_settings.openai_model = "gpt-4o-mini"
    fake_settings.openai_timeout = 30
    fake_settings.openai_max_retries = 3

    fake_settings.anthropic_enabled = False
    fake_settings.anthropic_api_key = None

    with (
        patch(
            "ai_news_digest.bootstrap.container.get_settings",
            return_value=fake_settings,
        ),
        patch(
            "ai_news_digest.bootstrap.container.LLMProviderFactory.create_openai_provider",
            return_value=AIProvider(provider_id="openai", provider_name="openai"),
        ) as create_openai,
    ):
        container = Container(MagicMock(spec=AsyncSession))

    # ProviderConfig must carry the provider name and configured API key.
    config: ProviderConfig = create_openai.call_args.args[0]
    assert config.provider_name == "openai"
    assert config.api_key == "test-openai-key"

    # The provider must be registered under its immutable id.
    assert container.provider_registry.exists("openai")
    assert "openai" in container.provider_registry

    # Both capabilities must be wired to the provider.
    assert "openai" in container.capability_registry.providers_for("summarization")
    assert "openai" in container.capability_registry.providers_for("categorization")

    # The decision engine must resolve the summarization capability.
    assert container.decision_engine.resolve({"summarization"}) == {"openai"}


def test_container_provider_registration_anthropic(monkeypatch) -> None:
    """Test that Anthropic provider registration works when an API key is configured."""
    from unittest.mock import MagicMock, patch

    fake_settings = MagicMock()
    fake_settings.openai_enabled = False
    fake_settings.openai_api_key = None

    fake_settings.anthropic_enabled = True
    fake_settings.anthropic_api_key = SecretStr("test-anthropic-key")
    fake_settings.anthropic_priority = 2
    fake_settings.anthropic_model = "claude-3-5-sonnet"
    fake_settings.anthropic_timeout = 30
    fake_settings.anthropic_max_retries = 3

    with (
        patch(
            "ai_news_digest.bootstrap.container.get_settings",
            return_value=fake_settings,
        ),
        patch(
            "ai_news_digest.bootstrap.container.LLMProviderFactory.create_anthropic_provider",
            return_value=AIProvider(provider_id="anthropic", provider_name="anthropic"),
        ) as create_anthropic,
    ):
        container = Container(MagicMock(spec=AsyncSession))

    config = create_anthropic.call_args.args[0]
    assert config.provider_name == "anthropic"
    assert config.api_key == "test-anthropic-key"

    assert container.provider_registry.exists("anthropic")
    assert "anthropic" in container.capability_registry.providers_for("summarization")
    assert "anthropic" in container.capability_registry.providers_for("categorization")

    assert container.decision_engine.resolve({"categorization"}) == {"anthropic"}


def test_container_unwraps_secretstr_api_keys() -> None:
    """Regression test: Container must unwrap SecretStr keys before passing to ProviderConfig."""
    from unittest.mock import MagicMock, patch

    from ai_news_digest.application.ai.config import ProviderConfig

    fake_settings = MagicMock()
    fake_settings.openai_enabled = True
    fake_settings.openai_api_key = SecretStr("sk-openai-secret")
    fake_settings.openai_priority = 1
    fake_settings.openai_model = "gpt-4o-mini"
    fake_settings.openai_timeout = 30
    fake_settings.openai_max_retries = 3

    fake_settings.anthropic_enabled = True
    fake_settings.anthropic_api_key = SecretStr("sk-ant-secret")
    fake_settings.anthropic_priority = 2
    fake_settings.anthropic_model = "claude-3-5-sonnet"
    fake_settings.anthropic_timeout = 30
    fake_settings.anthropic_max_retries = 3

    captured_configs: list[ProviderConfig] = []

    def fake_create_openai(config: ProviderConfig) -> AIProvider:
        captured_configs.append(config)
        return AIProvider(provider_id="openai", provider_name="openai")

    def fake_create_anthropic(config: ProviderConfig) -> AIProvider:
        captured_configs.append(config)
        return AIProvider(provider_id="anthropic", provider_name="anthropic")

    with (
        patch(
            "ai_news_digest.bootstrap.container.get_settings",
            return_value=fake_settings,
        ),
        patch(
            "ai_news_digest.bootstrap.container.LLMProviderFactory.create_openai_provider",
            side_effect=fake_create_openai,
        ),
        patch(
            "ai_news_digest.bootstrap.container.LLMProviderFactory.create_anthropic_provider",
            side_effect=fake_create_anthropic,
        ),
    ):
        container = Container(MagicMock(spec=AsyncSession))

    assert len(captured_configs) == 2

    openai_config = captured_configs[0]
    assert openai_config.provider_name == "openai"
    assert openai_config.api_key == "sk-openai-secret"
    assert not isinstance(openai_config.api_key, SecretStr)

    anthropic_config = captured_configs[1]
    assert anthropic_config.provider_name == "anthropic"
    assert anthropic_config.api_key == "sk-ant-secret"
    assert not isinstance(anthropic_config.api_key, SecretStr)

    assert container.provider_registry.exists("openai")
    assert container.provider_registry.exists("anthropic")
