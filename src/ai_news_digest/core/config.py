import json
from functools import lru_cache
from typing import Any, Literal

from pydantic import Field, SecretStr, ValidationInfo, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central application configuration.

    Configuration is loaded in the following order:

    1. Environment variables
    2. .env file
    3. Default values

    Environment variables always take precedence.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        frozen=True,
    )

    # ======================================================================
    # Server
    # ======================================================================

    host: str = Field(
        default="127.0.0.1",
        description="Host to bind the ASGI server to. Render requires 0.0.0.0.",
    )

    port: int = Field(
        default=8000,
        ge=1,
        le=65535,
        description="Port for the ASGI server. Render provides PORT env var.",
    )

    # ======================================================================
    # Application
    # ======================================================================

    app_name: str = "AI News Digest"

    app_version: str = "0.1.0"

    environment: Literal[
        "development",
        "testing",
        "staging",
        "production",
    ] = "development"

    debug: bool = False

    api_prefix: str = "/api/v1"

    app_startup_time: float | None = Field(
        default=None,
        description="Unix timestamp when the application finished startup.",
    )

    # ======================================================================
    # Database
    # ======================================================================

    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/ai_news_digest",
        validation_alias="DATABASE_URL",
        description=(
            "PostgreSQL connection URL. It is translated at the SQLAlchemy/Alembic "
            "connection boundary for asyncpg compatibility."
        ),
    )

    database_pool_size: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Database connection pool size.",
    )

    database_max_overflow: int = Field(
        default=10,
        ge=0,
        le=100,
        description="Database connection pool max overflow.",
    )

    database_pool_timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Database connection pool timeout in seconds.",
    )

    database_pool_recycle: int = Field(
        default=1800,
        ge=60,
        le=86400,
        description="Database connection pool recycle time in seconds.",
    )

    database_statement_timeout: int = Field(
        default=30000,
        ge=1000,
        le=300000,
        description="Database statement timeout in milliseconds.",
    )

    # ======================================================================
    # Redis
    # ======================================================================

    redis_url: str = Field(
        default="redis://localhost:6379/0",
        validation_alias="REDIS_URL",
        description="Redis connection URL.",
    )

    redis_socket_connect_timeout: int = Field(
        default=5,
        ge=1,
        le=60,
        description="Redis socket connect timeout in seconds.",
    )

    redis_socket_timeout: int = Field(
        default=5,
        ge=1,
        le=60,
        description="Redis socket timeout in seconds.",
    )

    redis_max_connections: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Redis maximum connection pool size.",
    )

    redis_retry_on_timeout: bool = Field(
        default=True,
        description="Retry Redis operations on timeout.",
    )

    redis_retry_on_connection_error: bool = Field(
        default=True,
        description="Retry Redis operations on connection error.",
    )

    # ======================================================================
    # Celery
    # ======================================================================

    celery_broker_url: str = Field(
        default="redis://localhost:6379/1",
        validation_alias="CELERY_BROKER_URL",
        description="Celery broker URL.",
    )

    celery_result_backend: str = Field(
        default="redis://localhost:6379/2",
        validation_alias="CELERY_RESULT_BACKEND",
        description="Celery result backend.",
    )

    # ======================================================================
    # LLM Providers
    # ======================================================================

    openai_api_key: SecretStr | None = Field(
        default=None,
        validation_alias="OPENAI_API_KEY",
    )

    openai_enabled: bool = Field(
        default=False,
        validation_alias="OPENAI_ENABLED",
    )

    openai_model: str = Field(
        default="gpt-4",
        validation_alias="OPENAI_MODEL",
    )

    openai_priority: int = Field(
        default=1,
        ge=1,
        validation_alias="OPENAI_PRIORITY",
    )

    openai_timeout: int = Field(
        default=30,
        ge=1,
        validation_alias="OPENAI_TIMEOUT",
    )

    openai_max_retries: int = Field(
        default=3,
        ge=0,
        validation_alias="OPENAI_MAX_RETRIES",
    )

    anthropic_api_key: SecretStr | None = Field(
        default=None,
        validation_alias="ANTHROPIC_API_KEY",
    )

    anthropic_enabled: bool = Field(
        default=False,
        validation_alias="ANTHROPIC_ENABLED",
    )

    anthropic_model: str = Field(
        default="claude-3-opus-20240229",
        validation_alias="ANTHROPIC_MODEL",
    )

    anthropic_priority: int = Field(
        default=2,
        ge=1,
        validation_alias="ANTHROPIC_PRIORITY",
    )

    anthropic_timeout: int = Field(
        default=30,
        ge=1,
        validation_alias="ANTHROPIC_TIMEOUT",
    )

    anthropic_max_retries: int = Field(
        default=3,
        ge=0,
        validation_alias="ANTHROPIC_MAX_RETRIES",
    )

    gemini_api_key: SecretStr | None = Field(
        default=None,
        validation_alias="GEMINI_API_KEY",
    )

    gemini_enabled: bool = Field(
        default=False,
        validation_alias="GEMINI_ENABLED",
    )

    gemini_model: str = Field(
        default="gemini-2.0-flash",
        validation_alias="GEMINI_MODEL",
    )

    gemini_priority: int = Field(
        default=3,
        ge=1,
        validation_alias="GEMINI_PRIORITY",
    )

    gemini_timeout: int = Field(
        default=30,
        ge=1,
        validation_alias="GEMINI_TIMEOUT",
    )

    gemini_max_retries: int = Field(
        default=3,
        ge=0,
        validation_alias="GEMINI_MAX_RETRIES",
    )

    xai_api_key: SecretStr | None = Field(
        default=None,
        validation_alias="XAI_API_KEY",
    )

    xai_enabled: bool = Field(
        default=False,
        validation_alias="XAI_ENABLED",
    )

    xai_model: str = Field(
        default="grok-2-latest",
        validation_alias="XAI_MODEL",
    )

    xai_priority: int = Field(
        default=4,
        ge=1,
        validation_alias="XAI_PRIORITY",
    )

    xai_timeout: int = Field(
        default=30,
        ge=1,
        validation_alias="XAI_TIMEOUT",
    )

    xai_max_retries: int = Field(
        default=3,
        ge=0,
        validation_alias="XAI_MAX_RETRIES",
    )

    # ======================================================================
    # AI Provider Quota & Pricing (M79)
    # ======================================================================

    openai_request_limit: int = Field(
        default=0,
        ge=0,
        validation_alias="OPENAI_REQUEST_LIMIT",
        description="Maximum requests per window for OpenAI. 0 means unlimited.",
    )

    openai_token_limit: int = Field(
        default=0,
        ge=0,
        validation_alias="OPENAI_TOKEN_LIMIT",
        description="Maximum tokens per window for OpenAI. 0 means unlimited.",
    )

    openai_cost_limit: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias="OPENAI_COST_LIMIT",
        description="Maximum cost per window for OpenAI in USD. 0 means unlimited.",
    )

    openai_input_cost_per_1k_tokens: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias="OPENAI_INPUT_COST_PER_1K_TOKENS",
        description="Input cost per 1k tokens for OpenAI in USD. 0 means unknown.",
    )

    openai_output_cost_per_1k_tokens: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias="OPENAI_OUTPUT_COST_PER_1K_TOKENS",
        description="Output cost per 1k tokens for OpenAI in USD. 0 means unknown.",
    )

    anthropic_request_limit: int = Field(
        default=0,
        ge=0,
        validation_alias="ANTHROPIC_REQUEST_LIMIT",
        description="Maximum requests per window for Anthropic. 0 means unlimited.",
    )

    anthropic_token_limit: int = Field(
        default=0,
        ge=0,
        validation_alias="ANTHROPIC_TOKEN_LIMIT",
        description="Maximum tokens per window for Anthropic. 0 means unlimited.",
    )

    anthropic_cost_limit: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias="ANTHROPIC_COST_LIMIT",
        description="Maximum cost per window for Anthropic in USD. 0 means unlimited.",
    )

    anthropic_input_cost_per_1k_tokens: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias="ANTHROPIC_INPUT_COST_PER_1K_TOKENS",
        description="Input cost per 1k tokens for Anthropic in USD. 0 means unknown.",
    )

    anthropic_output_cost_per_1k_tokens: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias="ANTHROPIC_OUTPUT_COST_PER_1K_TOKENS",
        description="Output cost per 1k tokens for Anthropic in USD. 0 means unknown.",
    )

    gemini_request_limit: int = Field(
        default=0,
        ge=0,
        validation_alias="GEMINI_REQUEST_LIMIT",
        description="Maximum requests per window for Gemini. 0 means unlimited.",
    )

    gemini_token_limit: int = Field(
        default=0,
        ge=0,
        validation_alias="GEMINI_TOKEN_LIMIT",
        description="Maximum tokens per window for Gemini. 0 means unlimited.",
    )

    gemini_cost_limit: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias="GEMINI_COST_LIMIT",
        description="Maximum cost per window for Gemini in USD. 0 means unlimited.",
    )

    gemini_input_cost_per_1k_tokens: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias="GEMINI_INPUT_COST_PER_1K_TOKENS",
        description="Input cost per 1k tokens for Gemini in USD. 0 means unknown.",
    )

    gemini_output_cost_per_1k_tokens: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias="GEMINI_OUTPUT_COST_PER_1K_TOKENS",
        description="Output cost per 1k tokens for Gemini in USD. 0 means unknown.",
    )

    xai_request_limit: int = Field(
        default=0,
        ge=0,
        validation_alias="XAI_REQUEST_LIMIT",
        description="Maximum requests per window for xAI Grok. 0 means unlimited.",
    )

    xai_token_limit: int = Field(
        default=0,
        ge=0,
        validation_alias="XAI_TOKEN_LIMIT",
        description="Maximum tokens per window for xAI Grok. 0 means unlimited.",
    )

    xai_cost_limit: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias="XAI_COST_LIMIT",
        description="Maximum cost per window for xAI Grok in USD. 0 means unlimited.",
    )

    xai_input_cost_per_1k_tokens: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias="XAI_INPUT_COST_PER_1K_TOKENS",
        description="Input cost per 1k tokens for xAI Grok in USD. 0 means unknown.",
    )

    xai_output_cost_per_1k_tokens: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias="XAI_OUTPUT_COST_PER_1K_TOKENS",
        description="Output cost per 1k tokens for xAI Grok in USD. 0 means unknown.",
    )

    default_llm_provider: Literal[
        "openai",
        "anthropic",
        "gemini",
        "grok",
    ] = "openai"

    # ==================================================================
    # AI Processing
    # ==================================================================

    ai_enabled: bool = Field(
        default=False,
        description=(
            "Master switch for all AI processing. When false, no AI providers "
            "are registered and no AI processing occurs regardless of individual "
            "provider enable flags. Requires intentional configuration to activate."
        ),
    )

    ai_max_content_length: int = Field(
        default=8000,
        ge=500,
        le=200000,
        description="Maximum article content characters sent to a provider.",
    )

    ai_summarization_max_tokens: int = Field(
        default=512,
        ge=64,
        le=4096,
        description="Maximum output tokens for summarization.",
    )

    ai_summarization_temperature: float = Field(
        default=0.2,
        ge=0.0,
        le=2.0,
        description="Generation temperature for summarization.",
    )

    ai_categorization_max_tokens: int = Field(
        default=64,
        ge=16,
        le=512,
        description="Maximum output tokens for categorization.",
    )

    ai_categorization_temperature: float = Field(
        default=0.1,
        ge=0.0,
        le=2.0,
        description="Generation temperature for categorization.",
    )

    ai_retry_max_attempts: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum retry attempts for transient provider failures.",
    )

    ai_retry_base_delay: float = Field(
        default=1.0,
        ge=0.0,
        le=60.0,
        description="Base delay in seconds for exponential backoff.",
    )

    ai_retry_max_delay: float = Field(
        default=10.0,
        ge=0.0,
        le=300.0,
        description="Maximum delay in seconds for exponential backoff.",
    )

    ai_provider_failure_threshold: int = Field(
        default=3,
        ge=1,
        le=100,
        description="Consecutive qualifying failures before a provider circuit opens.",
    )

    ai_provider_circuit_cooldown_seconds: float = Field(
        default=60.0,
        ge=0.0,
        le=86400.0,
        description="Cooldown duration in seconds before an open circuit can be probed.",
    )

    ai_provider_half_open_probe_timeout_seconds: float = Field(
        default=30.0,
        gt=0.0,
        le=300.0,
        description="Timeout in seconds for half-open probe requests.",
    )

    ai_provider_success_threshold_to_close: int = Field(
        default=1,
        ge=1,
        le=10,
        description="Consecutive successes required to close a half-open circuit.",
    )

    # ======================================================================
    # Semantic Intelligence and Embedding (M88)
    # ======================================================================

    semantic_search_enabled: bool = Field(
        default=False,
        description=(
            "Enable semantic search and related-story discovery. When false, "
            "the platform falls back to lexical search and deterministic "
            "ranking. Requires an embedding provider to be configured."
        ),
    )

    embedding_provider: str = Field(
        default="openai",
        description="Default embedding provider identifier.",
    )

    embedding_model: str = Field(
        default="text-embedding-3-small",
        description="Default embedding model name.",
    )

    embedding_dimension: int = Field(
        default=1536,
        ge=1,
        le=4096,
        description="Expected embedding dimension for the configured model.",
    )

    semantic_search_query_max_length: int = Field(
        default=500,
        ge=1,
        le=2000,
        description="Maximum characters accepted for a semantic search query.",
    )

    semantic_candidate_limit: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Maximum candidate articles/clusters for semantic processing.",
    )

    semantic_result_limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum results returned from semantic-enhanced endpoints.",
    )

    semantic_lexical_weight: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="Weight for lexical relevance in hybrid search ranking.",
    )

    semantic_similarity_weight: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="Weight for semantic similarity in hybrid search ranking.",
    )

    semantic_importance_weight: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Weight for article importance in hybrid search ranking.",
    )

    semantic_recency_weight: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Weight for recency in hybrid search ranking.",
    )

    # ======================================================================
    # AI Cost & Quota (M79)
    # ======================================================================

    ai_daily_cost_budget: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias="AI_DAILY_COST_BUDGET",
        description=(
            "Daily global AI cost budget in USD. "
            "When 0 (default), no daily budget limit is enforced."
        ),
    )

    ai_monthly_cost_budget: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias="AI_MONTHLY_COST_BUDGET",
        description=(
            "Monthly global AI cost budget in USD. "
            "When 0 (default), no monthly budget limit is enforced."
        ),
    )

    ai_max_estimated_request_cost: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias="AI_MAX_ESTIMATED_REQUEST_COST",
        description=(
            "Maximum estimated cost per individual AI request in USD. "
            "When 0 (default), no per-request cost cap is enforced."
        ),
    )

    # ======================================================================
    # RSS
    # ======================================================================

    rss_request_timeout: int = Field(
        default=20,
        ge=1,
        le=120,
    )

    rss_max_articles_per_feed: int = Field(
        default=50,
        ge=1,
        le=500,
    )

    rss_max_response_bytes: int = Field(
        default=5_000_000,
        ge=1_000,
        le=100_000_000,
        description=(
            "Maximum accepted RSS/Atom feed response body size in bytes. "
            "Larger responses are rejected to bound memory usage."
        ),
    )

    # ======================================================================
    # Article Extraction
    # ======================================================================

    article_fetch_timeout: int = Field(
        default=20,
        ge=1,
        le=120,
        description="Timeout for article HTTP fetches in seconds.",
    )

    article_max_response_bytes: int = Field(
        default=5_000_000,
        ge=1_000,
        le=100_000_000,
        description="Maximum article HTTP response body size in bytes.",
    )

    article_max_redirects: int = Field(
        default=5,
        ge=0,
        le=20,
        description="Maximum redirect hops for article fetches.",
    )

    extraction_min_content_length: int = Field(
        default=200,
        ge=0,
        le=5000,
        description="Minimum extracted content length to consider extraction successful.",
    )

    extraction_enabled: bool = Field(
        default=True,
        description="Enable article content extraction during ingestion.",
    )

    # ======================================================================
    # Story Clustering
    # ======================================================================

    story_clustering_enabled: bool = Field(
        default=True,
        description="Enable semantic story clustering after AI analysis.",
    )

    story_semantic_duplicate_threshold: float = Field(
        default=0.65,
        ge=0.0,
        le=1.0,
        description=(
            "Minimum similarity score for an article to be considered a "
            "semantic duplicate of an existing story cluster. Values above "
            "this threshold merge articles into the same cluster. Conservative "
            "defaults are used to avoid false-positive merges."
        ),
    )

    story_related_story_threshold: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description=(
            "Similarity score above which articles are classified as related "
            "but distinct stories. Scores below this are new stories. Must be "
            "lower than story_semantic_duplicate_threshold."
        ),
    )

    story_time_window_hours: int = Field(
        default=72,
        ge=1,
        le=720,
        description=(
            "Maximum age of existing clusters/articles (in hours) to consider "
            "as clustering candidates. Older stories are not automatically "
            "merged."
        ),
    )

    story_candidate_limit: int = Field(
        default=50,
        ge=1,
        le=500,
        description=(
            "Maximum number of candidate clusters/articles to evaluate for "
            "each new article. Bounding this avoids O(n²) behavior."
        ),
    )

    @field_validator("story_related_story_threshold")
    @classmethod
    def validate_related_threshold(
        cls, value: float, info: ValidationInfo
    ) -> float:
        semantic = info.data.get("story_semantic_duplicate_threshold")
        if semantic is not None and value >= semantic:
            raise ValueError(
                "story_related_story_threshold must be lower than "
                "story_semantic_duplicate_threshold."
            )
        return value

    # ======================================================================
    # Digest
    # ======================================================================

    digest_timezone: str = Field(
        default="UTC",
        description=(
            "IANA timezone name used by digest scheduling and digest titles. "
            "Must be a valid IANA timezone (e.g. 'UTC', 'Europe/London', "
            "'Asia/Kolkata'). The default of UTC is the safest choice for "
            "backwards compatibility; the digest schedule runs at "
            "DIGEST_SCHEDULE_HOUR:DIGEST_SCHEDULE_MINUTE in this timezone."
        ),
    )

    digest_schedule_hour: int = Field(
        default=8,
        ge=0,
        le=23,
        description=(
            "Hour of the day (in ``digest_timezone``) when the daily digest "
            "generation task runs. This must be scheduled AFTER the daily "
            "story ranking task to ensure ranking data is available."
        ),
    )

    digest_schedule_minute: int = Field(
        default=15,
        ge=0,
        le=59,
        description=(
            "Minute of the hour when the daily digest generation task runs. "
            "The default of 15 ensures digest generation runs after the "
            "default 08:05 daily story ranking task."
        ),
    )

    digest_max_articles: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Maximum number of articles included in a single digest.",
    )

    # ======================================================================
    # Intelligent Digest Editorial (M69)
    # ======================================================================

    digest_editorial_enabled: bool = Field(
        default=True,
        description="Enable intelligent editorial generation for daily digests.",
    )

    digest_max_editorial_stories: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of stories in the intelligent editorial digest.",
    )

    digest_editorial_prompt_version: str = Field(
        default="v1",
        description="Prompt version for digest editorial generation.",
    )

    digest_editorial_timeout: int = Field(
        default=60,
        ge=10,
        le=300,
        description="Timeout in seconds for editorial LLM generation.",
    )

    digest_editorial_max_tokens: int = Field(
        default=2048,
        ge=256,
        le=8192,
        description="Maximum output tokens for editorial generation.",
    )

    digest_editorial_temperature: float = Field(
        default=0.3,
        ge=0.0,
        le=2.0,
        description="Generation temperature for editorial content.",
    )

    digest_fallback_enabled: bool = Field(
        default=True,
        description="Enable deterministic fallback when AI editorial generation fails.",
    )

    # ======================================================================
    # Story Ranking (M68)
    # ======================================================================

    story_ranking_enabled: bool = Field(
        default=True,
        description="Enable deterministic story cluster ranking before digest generation.",
    )

    ranking_lookback_hours: int = Field(
        default=24,
        ge=1,
        le=720,
        description="Lookback window in hours for daily ranking/Top Story selection.",
    )

    ranking_max_candidates: int = Field(
        default=200,
        ge=1,
        le=500,
        description="Maximum number of StoryClusters to evaluate during ranking.",
    )

    ranking_recency_weight: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description="Weight for the recency signal in story ranking.",
    )

    ranking_source_trust_weight: float = Field(
        default=0.20,
        ge=0.0,
        le=1.0,
        description="Weight for the source trust signal in story ranking.",
    )

    ranking_source_diversity_weight: float = Field(
        default=0.10,
        ge=0.0,
        le=1.0,
        description="Weight for the source diversity signal in story ranking.",
    )

    ranking_corroboration_weight: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description="Weight for the corroboration signal in story ranking.",
    )

    ranking_company_relevance_weight: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description="Weight for the company relevance signal in story ranking.",
    )

    ranking_category_topic_relevance_weight: float = Field(
        default=0.10,
        ge=0.0,
        le=1.0,
        description="Weight for the category/topic relevance signal in story ranking.",
    )

    ranking_article_quality_weight: float = Field(
        default=0.10,
        ge=0.0,
        le=1.0,
        description="Weight for the article quality signal in story ranking.",
    )

    ranking_official_announcement_weight: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="Weight for the official announcement signal in story ranking.",
    )

    ranking_recency_decay_hours: float = Field(
        default=24.0,
        ge=1.0,
        le=720.0,
        description="Decay half-life in hours for the recency signal.",
    )

    # ======================================================================
    # Claim Extraction (M81)
    # ======================================================================

    claim_extraction_enabled: bool = Field(
        default=True,
        description="Enable claim extraction during article analysis.",
    )

    claim_max_claims_per_article: int = Field(
        default=15,
        ge=1,
        le=50,
        description="Maximum number of claims to extract per article.",
    )

    claim_max_evidence_per_claim: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of evidence items per claim.",
    )

    claim_max_claim_length: int = Field(
        default=500,
        ge=50,
        le=2000,
        description="Maximum character length for a claim text.",
    )

    claim_max_excerpt_length: int = Field(
        default=200,
        ge=20,
        le=1000,
        description="Maximum character length for an evidence excerpt.",
    )

    # ======================================================================
    # Cross-Source Conflict Detection (M82)
    # ======================================================================

    conflict_detection_enabled: bool = Field(
        default=True,
        description="Enable cross-source claim conflict detection.",
    )

    conflict_detection_max_claims: int = Field(
        default=200,
        ge=1,
        le=2000,
        description="Maximum number of recent claims to consider per run.",
    )

    conflict_detection_max_candidates: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum candidate pairs to consider per claim.",
    )

    conflict_detection_max_comparisons: int = Field(
        default=200,
        ge=1,
        le=2000,
        description="Maximum total claim-pair comparisons per run.",
    )

    conflict_detection_max_llm_comparisons: int = Field(
        default=20,
        ge=0,
        le=200,
        description="Maximum LLM-assisted ambiguity checks per run.",
    )

    conflict_detection_temporal_window_hours: float = Field(
        default=72.0,
        ge=1.0,
        le=720.0,
        description=(
            "Maximum publication time difference (hours) for claims to be "
            "considered temporally comparable."
        ),
    )

    conflict_detection_confidence_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum confidence to persist a potential conflict.",
    )

    # ======================================================================
    # Breaking & Developing Story Detection (M83)
    # ======================================================================

    breaking_detection_enabled: bool = Field(
        default=True,
        description="Enable breaking and developing story activity detection.",
    )

    breaking_window_hours: int = Field(
        default=6,
        ge=1,
        le=72,
        description=(
            "Lookback window in hours for breaking story detection. "
            "Articles published within this window are considered for breaking status."
        ),
    )

    developing_window_hours: int = Field(
        default=24,
        ge=1,
        le=168,
        description=(
            "Lookback window in hours for developing story detection. "
            "Articles published within this window are considered for developing status."
        ),
    )

    stale_window_hours: int = Field(
        default=72,
        ge=1,
        le=720,
        description=(
            "Lookback window in hours for stale story detection. "
            "Stories with no articles within this window are marked stale."
        ),
    )

    max_story_candidates: int = Field(
        default=200,
        ge=1,
        le=1000,
        description="Maximum number of story clusters to evaluate per run.",
    )

    max_articles_per_story: int = Field(
        default=50,
        ge=1,
        le=200,
        description="Maximum number of recent articles to load per story cluster.",
    )

    max_claims_per_story: int = Field(
        default=50,
        ge=1,
        le=200,
        description="Maximum number of recent claims to consider per story cluster.",
    )

    max_llm_evaluations: int = Field(
        default=10,
        ge=0,
        le=100,
        description="Maximum LLM ambiguity checks per breaking detection run.",
    )

    breaking_threshold: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description=(
            "Minimum activity score for BREAKING classification. "
            "Conservative default to reduce false positives."
        ),
    )

    developing_threshold: float = Field(
        default=0.45,
        ge=0.0,
        le=1.0,
        description=(
            "Minimum activity score for DEVELOPING classification. "
            "Must be lower than breaking_threshold."
        ),
    )

    minimum_independent_sources: int = Field(
        default=3,
        ge=1,
        le=20,
        description=(
            "Minimum number of independent trusted sources required "
            "for authoritative breaking/developing classification."
        ),
    )

    @field_validator("developing_threshold")
    @classmethod
    def validate_developing_threshold(
        cls, value: float, info: ValidationInfo
    ) -> float:
        breaking = info.data.get("breaking_threshold")
        if breaking is not None and value >= breaking:
            raise ValueError(
                "developing_threshold must be lower than breaking_threshold."
            )
        return value

    # ======================================================================
    # Story Evolution / Event Timeline (M84)
    # ======================================================================

    timeline_generation_enabled: bool = Field(
        default=True,
        description="Enable story evolution timeline generation.",
    )

    timeline_max_articles_per_event: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum articles to associate with a single timeline event.",
    )

    timeline_max_claims_per_event: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum claims to associate with a single timeline event.",
    )

    timeline_max_events_per_cluster: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum timeline events per story cluster.",
    )

    timeline_lookback_days: int = Field(
        default=30,
        ge=1,
        le=365,
        description="Lookback window in days for timeline candidate articles.",
    )

    timeline_max_llm_evaluations: int = Field(
        default=10,
        ge=0,
        le=100,
        description="Maximum LLM-assisted event extractions per run.",
    )

    # ======================================================================
    # Trend Detection and Emerging Story Intelligence (M85)
    # ======================================================================

    trend_detection_enabled: bool = Field(
        default=True,
        description="Enable deterministic trend detection and emerging story intelligence.",
    )

    trend_recent_window_hours: int = Field(
        default=24,
        ge=1,
        le=720,
        description="Lookback window in hours for recent trend activity.",
    )

    trend_baseline_window_hours: int = Field(
        default=168,
        ge=1,
        le=720,
        description="Lookback window in hours for historical baseline activity.",
    )

    trend_min_recent_activity: int = Field(
        default=3,
        ge=1,
        le=100,
        description="Minimum recent article count required to consider a candidate.",
    )

    trend_min_sources: int = Field(
        default=2,
        ge=1,
        le=50,
        description="Minimum unique trusted sources required to consider a candidate.",
    )

    trend_max_candidates_per_type: int = Field(
        default=50,
        ge=1,
        le=500,
        description=(
            "Maximum candidates to evaluate per trend type "
            "(company, topic, category, story)."
        ),
    )

    trend_max_total_candidates: int = Field(
        default=200,
        ge=1,
        le=1000,
        description="Maximum total candidates evaluated per trend detection run.",
    )

    trend_activity_weight: float = Field(
        default=0.25,
        ge=0.0,
        le=1.0,
        description="Weight for recent article activity in trend scoring.",
    )

    trend_growth_weight: float = Field(
        default=0.25,
        ge=0.0,
        le=1.0,
        description="Weight for activity growth vs baseline in trend scoring.",
    )

    trend_source_diversity_weight: float = Field(
        default=0.20,
        ge=0.0,
        le=1.0,
        description="Weight for source diversity in trend scoring.",
    )

    trend_story_growth_weight: float = Field(
        default=0.10,
        ge=0.0,
        le=1.0,
        description="Weight for story cluster growth in trend scoring.",
    )

    trend_recency_weight: float = Field(
        default=0.10,
        ge=0.0,
        le=1.0,
        description="Weight for recency of latest activity in trend scoring.",
    )

    trend_event_weight: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="Weight for story event activity in trend scoring.",
    )

    trend_activity_boost_weight: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="Weight for M83 story activity status boost in trend scoring.",
    )

    # ======================================================================
    # Knowledge Graph (M89)
    # ======================================================================

    knowledge_graph_enabled: bool = Field(
        default=False,
        description=(
            "Enable knowledge graph relationship extraction and APIs. "
            "When false, relationship endpoints return empty results and "
            "no AI-derived relationships are created."
        ),
    )

    knowledge_graph_max_relationships_per_article: int = Field(
        default=5,
        ge=0,
        le=50,
        description="Maximum relationships to extract per article.",
    )

    knowledge_graph_max_relationships_per_story: int = Field(
        default=20,
        ge=0,
        le=200,
        description="Maximum relationships to extract per story cluster.",
    )

    knowledge_graph_max_nodes: int = Field(
        default=500,
        ge=1,
        le=10000,
        description="Maximum nodes to consider in graph traversal.",
    )

    knowledge_graph_max_edges: int = Field(
        default=2000,
        ge=1,
        le=50000,
        description="Maximum edges to return in graph traversal.",
    )

    # ======================================================================
    # Email / SMTP
    # ======================================================================

    email_enabled: bool = Field(
        default=True,
        description="Enable email notification delivery.",
    )

    email_provider: Literal["console", "smtp", "test"] = Field(
        default="console",
        description="Email provider backend: console (dev), smtp (production), test (testing).",
    )

    email_from_address: str = Field(
        default="noreply@ai-news-digest.com",
        description="From address for outgoing emails.",
    )

    email_from_name: str = Field(
        default="AI News Digest",
        description="From display name for outgoing emails.",
    )

    email_reply_to: str | None = Field(
        default=None,
        description="Reply-to address for outgoing emails.",
    )

    email_base_url: str = Field(
        default="",
        description="Base URL used in email links. Must be set in production.",
    )

    email_max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum retry attempts for transient email delivery failures.",
    )

    email_retry_delay: int = Field(
        default=60,
        ge=1,
        le=3600,
        description="Base retry delay in seconds for email delivery retries.",
    )

    email_batch_size: int = Field(
        default=50,
        ge=1,
        le=1000,
        description="Maximum number of emails sent in a single batch.",
    )

    email_rate_limit: int = Field(
        default=100,
        ge=1,
        le=10000,
        description="Maximum emails per rate limit window.",
    )

    email_timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Timeout in seconds for individual email delivery operations.",
    )

    email_development_mode: bool = Field(
        default=True,
        description="Force console email sender even in non-development environments.",
    )

    @field_validator("email_provider")
    @classmethod
    def validate_email_provider(cls, value: str) -> str:
        allowed = {"console", "smtp", "test"}
        normalized = value.strip().lower()
        if normalized not in allowed:
            raise ValueError(f"EMAIL_PROVIDER must be one of {sorted(allowed)}, got '{value}'.")
        return normalized

    # ======================================================================
    # Notification Retention
    # ======================================================================

    notification_retention_days: int = Field(
        default=90,
        ge=1,
        le=3650,
        description="Number of days to retain notification records.",
    )

    notification_delivery_retention_days: int = Field(
        default=30,
        ge=1,
        le=3650,
        description="Number of days to retain notification delivery records.",
    )

    @field_validator("smtp_port", mode="before")
    @classmethod
    def parse_smtp_port(cls, value: str | int) -> int:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return 587
            return int(stripped)
        return value

    smtp_host: str = Field(
        default="localhost",
        description="SMTP server hostname.",
    )

    smtp_port: int = Field(
        default=587,
        ge=1,
        le=65535,
        description="SMTP server port.",
    )

    smtp_user: str | None = Field(
        default=None,
        description="SMTP username.",
    )

    smtp_password: str | None = Field(
        default=None,
        description="SMTP password.",
    )

    email_from: str = Field(
        default="noreply@ai-news-digest.com",
        description="From address for outgoing emails.",
    )

    email_recipients: str | list[str] = Field(
        default_factory=list,
        description="List of email recipients for digests.",
    )

    # ======================================================================
    # Logging
    # ======================================================================

    log_level: Literal[
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
        "CRITICAL",
    ] = "INFO"

    sentry_dsn: str | None = Field(
        default=None,
        description="Sentry DSN for error tracking. Leave empty to disable Sentry.",
    )

    # ======================================================================
    # Authentication
    # ======================================================================

    jwt_secret_key: str = Field(
        default="ci-fake-jwt-secret-for-testing-only-2026",
        description="Secret key for signing JWT tokens.",
    )

    jwt_algorithm: str = Field(
        default="HS256",
        description="Algorithm used for JWT signing.",
    )

    jwt_expiration_minutes: int = Field(
        default=60,
        ge=1,
        description="Access token expiration time in minutes.",
    )

    bcrypt_rounds: int = Field(
        default=12,
        ge=4,
        le=31,
        description="Cost factor (rounds) for bcrypt password hashing.",
    )

    # ======================================================================
    # Authentication Tradeoffs
    # ======================================================================
    #
    # This application uses stateless JWT access tokens without refresh tokens
    # or a revocation blacklist. The security tradeoff is that a compromised
    # token remains valid until its expiration time (default: 60 minutes).
    # For the current architecture (no refresh tokens, short-lived access
    # tokens), this is an acceptable risk. If the architecture evolves to
    # include refresh tokens or longer-lived sessions, a token revocation
    # mechanism should be implemented.
    #

    cors_origins: str | list[str] | None = Field(
        default=None,
        description=(
            "Allowed CORS origins. Defaults to localhost in development "
            "and an empty list in production."
        ),
    )

    rate_limit: int = Field(
        default=60,
        ge=1,
        le=10000,
        description="Maximum requests per rate limit window.",
    )

    rate_limit_window: int = Field(
        default=60,
        ge=1,
        le=3600,
        description="Rate limit window in seconds.",
    )

    auth_rate_limit: int = Field(
        default=10,
        ge=1,
        le=10000,
        description="Maximum auth-endpoint requests per rate limit window.",
    )

    auth_rate_limit_window: int = Field(
        default=60,
        ge=1,
        le=3600,
        description="Auth-endpoint rate limit window in seconds.",
    )

    auth_max_failed_attempts: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Maximum failed login attempts before account lockout.",
    )

    auth_lockout_seconds: int = Field(
        default=300,
        ge=30,
        le=86400,
        description="Base lockout duration in seconds after too many failed logins.",
    )

    max_request_size_bytes: int = Field(
        default=1_048_576,
        ge=1024,
        le=50_000_000,
        description="Maximum allowed HTTP request body size in bytes.",
    )

    metrics_allowed_ips: str | list[str] = Field(
        default_factory=list,
        description=(
            "Optional list of client IP addresses permitted to access the "
            "/metrics endpoint. When empty, access is governed solely by the "
            "admin authentication requirement. In production this should be "
            "restricted to monitoring/metrics scrapers."
        ),
    )

    @field_validator(
        "email_recipients",
        "cors_origins",
        "metrics_allowed_ips",
        mode="before",
    )
    @classmethod
    def parse_list_from_env(cls, value: str | list[str] | None) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return []
            try:
                parsed = json.loads(stripped)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass
            return [item.strip() for item in stripped.split(",") if item.strip()]
        return value

    @field_validator("jwt_algorithm")
    @classmethod
    def validate_jwt_algorithm(cls, value: str) -> str:
        """Reject the 'none' algorithm to prevent algorithm-confusion attacks."""
        if value.strip().lower() == "none":
            raise ValueError("JWT algorithm 'none' is not allowed.")
        return value

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret(cls, value: str, info: ValidationInfo) -> str:
        """Ensure JWT secret is not a known weak default.

        Placeholder secrets are only rejected in non-development environments.
        In development mode, any non-empty value is accepted so that the
        example configuration and quick-starts work out of the box.
        In testing mode, weak secrets are accepted but must still meet
        minimum length requirements.
        """
        environment = info.data.get("environment", "development")
        if environment == "development":
            return value
        if environment == "testing":
            if len(value.strip()) < 32:
                raise ValueError("JWT_SECRET_KEY must be at least 32 characters long.")
            return value
        weak_defaults = {
            "change-me",
            "changeme",
            "secret",
            "dev-secret-key-change-me-in-production",
            "replace-me-with-a-secure-random-string-at-least-32-chars",
            "your-secret-key-here",
            "insecure",
            "password",
            "12345678901234567890123456789012",
            "ci-fake-jwt-secret-for-testing-only-2026",
        }
        weak_patterns = (
            "change_me",
            "changeme",
            "change-me",
            "replace-me",
            "replace_me",
            "please-replace",
            "your-openssl-rand",
            "test-secret",
            "test_secret",
            "placeholder",
            "dev_secret",
            "do-not-use",
            "not-for-production",
            "not_for_production",
            "local-prod",
            "local_dev",
            "fake-key",
            "fake_key",
            "testing-only",
            "ci-fake",
            "your-secret-key-here",
            "your_secret_key_here",
            "use_openssl_rand",
            "change_me",
        )
        normalized = value.strip().lower()
        if normalized in weak_defaults:
            raise ValueError(
                "JWT_SECRET_KEY must be set to a secure value. "
                "The provided default is not allowed in any environment."
            )
        if any(pattern in normalized for pattern in weak_patterns):
            raise ValueError(
                "JWT_SECRET_KEY must be set to a secure value. "
                "The provided value resembles a placeholder."
            )
        if all(c in "0123456789abcdef" for c in normalized) and (
            "0123456789abcdef" in normalized or "abcdef0123456789" in normalized
        ):
            raise ValueError(
                "JWT_SECRET_KEY must be set to a cryptographically secure value. "
                "The provided value appears to be a sequential hex pattern."
            )
        if len(value) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters long.")
        return value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def validate_cors_origins(
        cls,
        value: str | list[str] | None,
        info: ValidationInfo,
    ) -> list[str]:
        """Set CORS defaults based on environment.

        Development and staging default to localhost origins.
        Production defaults to an empty list (fail closed).
        """
        if value is None or (isinstance(value, str) and not value.strip()):
            environment = info.data.get("environment", "development")
            if environment == "production":
                return []
            return ["http://localhost:3000", "http://localhost:8000"]
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return []
            try:
                parsed = json.loads(stripped)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass
            return [item.strip() for item in stripped.split(",") if item.strip()]
        return value

    @field_validator("digest_timezone")
    @classmethod
    def validate_digest_timezone(cls, value: str) -> str:
        """Validate that ``digest_timezone`` is a usable IANA timezone name."""
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

        candidate = (value or "").strip()
        if not candidate:
            raise ValueError("DIGEST_TIMEZONE must not be empty.")
        try:
            ZoneInfo(candidate)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(
                f"DIGEST_TIMEZONE '{candidate}' is not a valid IANA timezone name."
            ) from exc
        return candidate

    @field_validator("email_development_mode")
    @classmethod
    def validate_email_development_mode(cls, value: bool, info: ValidationInfo) -> bool:
        """Ensure email development mode is disabled in production."""
        environment = info.data.get("environment", "development")
        if environment == "production" and value:
            raise ValueError(
                "EMAIL_DEVELOPMENT_MODE must be 'false' in production. "
                "Emails must be delivered via the configured SMTP provider."
            )
        return value

    @field_validator("email_provider")
    @classmethod
    def validate_email_provider_production(cls, value: str, info: ValidationInfo) -> str:
        """Ensure production uses a real email provider when email is enabled."""
        environment = info.data.get("environment", "development")
        email_enabled = info.data.get("email_enabled", True)
        if environment == "production" and email_enabled and value == "console":
            raise ValueError(
                "EMAIL_PROVIDER must be 'smtp' in production when email is enabled. "
                "Console sender is for development only."
            )
        return value

    @field_validator("email_base_url")
    @classmethod
    def validate_email_base_url(cls, value: str, info: ValidationInfo) -> str:
        """Ensure email_base_url is set in production when email is enabled."""
        environment = info.data.get("environment", "development")
        email_enabled = info.data.get("email_enabled", True)
        if environment == "production" and email_enabled and not value.strip():
            raise ValueError(
                "EMAIL_BASE_URL must be set to the public application URL in production."
            )
        return value

    @field_validator("openai_api_key")
    @classmethod
    def validate_openai_api_key(
        cls, value: SecretStr | None, info: ValidationInfo
    ) -> SecretStr | None:
        """Ensure OPENAI_API_KEY is set when OpenAI is enabled in production."""
        environment = info.data.get("environment", "development")
        openai_enabled = info.data.get("openai_enabled", False)
        if environment == "production" and openai_enabled and not value:
            raise ValueError("OPENAI_API_KEY must be set when OPENAI_ENABLED=true in production.")
        return value

    @field_validator("anthropic_api_key")
    @classmethod
    def validate_anthropic_api_key(
        cls, value: SecretStr | None, info: ValidationInfo
    ) -> SecretStr | None:
        """Ensure ANTHROPIC_API_KEY is set when Anthropic is enabled in production."""
        environment = info.data.get("environment", "development")
        anthropic_enabled = info.data.get("anthropic_enabled", False)
        if environment == "production" and anthropic_enabled and not value:
            raise ValueError(
                "ANTHROPIC_API_KEY must be set when ANTHROPIC_ENABLED=true in production."
            )
        return value

    @model_validator(mode="after")
    def validate_ai_provider_keys(self) -> "Settings":
        """Cross-field validation for AI provider API keys after all fields are loaded."""
        environment = self.environment
        if environment == "production":
            if self.openai_enabled and not self.openai_api_key:
                raise ValueError(
                    "OPENAI_API_KEY must be set when OPENAI_ENABLED=true in production."
                )
            if self.anthropic_enabled and not self.anthropic_api_key:
                raise ValueError(
                    "ANTHROPIC_API_KEY must be set when ANTHROPIC_ENABLED=true in production."
                )
            if self.gemini_enabled and not self.gemini_api_key:
                raise ValueError(
                    "GEMINI_API_KEY must be set when GEMINI_ENABLED=true in production."
                )
            if self.xai_enabled and not self.xai_api_key:
                raise ValueError(
                    "XAI_API_KEY must be set when XAI_ENABLED=true in production."
                )
        return self

    @field_validator("smtp_host")
    @classmethod
    def validate_smtp_host(cls, value: str | None, info: ValidationInfo) -> str | None:
        """Ensure SMTP_HOST is set when email is enabled and provider is smtp in production."""
        environment = info.data.get("environment", "development")
        email_enabled = info.data.get("email_enabled", True)
        email_provider = info.data.get("email_provider", "console")
        if environment == "production" and email_enabled and email_provider == "smtp" and not value:
            raise ValueError("SMTP_HOST must be set when EMAIL_PROVIDER=smtp in production.")
        return value


class _LazySettingsMeta(type):
    def __instancecheck__(cls, instance: object) -> bool:
        if isinstance(instance, _LazySettings):
            return True
        return super().__instancecheck__(instance)


class _LazySettings(metaclass=_LazySettingsMeta):
    def __init__(self) -> None:
        self._loaded = False

    def _load(self) -> Settings:
        if not self._loaded:
            self._settings = get_settings()
            self._loaded = True
        return self._settings

    def __getattr__(self, name: str) -> Any:
        return getattr(self._load(), name)

    def __repr__(self) -> str:
        return repr(self._load())

    def __str__(self) -> str:
        return str(self._load())


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return a cached Settings instance.

    The configuration is instantiated once per process,
    avoiding repeated environment parsing.
    """
    return Settings()


settings = _LazySettings()
