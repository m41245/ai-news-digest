from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ai_news_digest.api.metrics import MetricsMiddleware
from ai_news_digest.api.metrics import router as metrics_router
from ai_news_digest.api.middleware.exception_handler import setup_exception_handlers
from ai_news_digest.api.middleware.logging import LoggingMiddleware
from ai_news_digest.api.middleware.rate_limit import RateLimitMiddleware
from ai_news_digest.api.middleware.request_id import RequestIDMiddleware
from ai_news_digest.api.middleware.request_size import MaxBodySizeMiddleware
from ai_news_digest.api.middleware.security_headers import SecurityHeadersMiddleware
from ai_news_digest.api.v1.routes.admin import router as admin_router
from ai_news_digest.api.v1.routes.articles import router as articles_router
from ai_news_digest.api.v1.routes.auth import router as auth_router
from ai_news_digest.api.v1.routes.categories import router as categories_router
from ai_news_digest.api.v1.routes.digests import router as digests_router
from ai_news_digest.api.v1.routes.health import router as health_router
from ai_news_digest.api.v1.routes.public import router as public_router
from ai_news_digest.api.v1.routes.sources import router as sources_router
from ai_news_digest.api.v1.routes.users import router as users_router
from ai_news_digest.core.config import Settings, get_settings
from ai_news_digest.core.logging import configure_logging, get_logger
from ai_news_digest.infrastructure.cache.redis_store import RedisStore

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app_settings = _get_app_settings(app)
    startup_time = datetime.now(UTC).timestamp()
    app_settings = app_settings.model_copy(
        update={"app_startup_time": startup_time},
    )
    app.extra["settings"] = app_settings

    logger.info(
        "Application starting",
        app_name=app_settings.app_name,
        version=app_settings.app_version,
        environment=app_settings.environment,
    )

    app.state.redis_store = RedisStore(app_settings.redis_url)

    try:
        yield
    finally:
        shutdown_reason = "normal_shutdown"
        logger.info(
            "Application shutting down",
            reason=shutdown_reason,
        )

        redis_store: RedisStore | None = getattr(app.state, "redis_store", None)
        if redis_store is not None:
            try:
                await redis_store.close()
            except Exception as exc:
                logger.error("Failed to close RedisStore during shutdown: %s", exc)

        try:
            from ai_news_digest.infrastructure.database.session import engine

            await engine.dispose()
        except Exception as exc:
            logger.error("Failed to dispose database engine during shutdown: %s", exc)

        logger.info("Application shutdown complete")


def _get_app_settings(app: FastAPI) -> Settings:
    """Retrieve the Settings instance associated with the app."""
    return app.extra.get("settings") or get_settings()


def create_app(settings_override: Settings | None = None) -> FastAPI:
    """
    Application factory.

    Builds and returns a configured FastAPI application instance.
    """
    app_settings = settings_override or get_settings()

    application = FastAPI(
        title=app_settings.app_name,
        version=app_settings.app_version,
        debug=app_settings.debug,
        lifespan=lifespan,
        openapi_url=(
            f"{app_settings.api_prefix}/openapi.json"
            if app_settings.environment != "production"
            else None
        ),
        docs_url="/docs" if app_settings.environment != "production" else None,
        redoc_url="/redoc" if app_settings.environment != "production" else None,
    )

    application.extra["settings"] = app_settings

    setup_exception_handlers(application)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    application.add_middleware(SecurityHeadersMiddleware)

    application.add_middleware(RequestIDMiddleware)
    application.add_middleware(LoggingMiddleware)
    application.add_middleware(
        RateLimitMiddleware,
        cache_store=RedisStore(app_settings.redis_url),
    )
    application.add_middleware(
        MaxBodySizeMiddleware,
        max_content_length=app_settings.max_request_size_bytes,
    )
    application.add_middleware(MetricsMiddleware)

    application.include_router(health_router)

    application.include_router(metrics_router)

    application.include_router(
        public_router,
        prefix=app_settings.api_prefix,
    )

    application.include_router(
        auth_router,
        prefix=app_settings.api_prefix,
    )

    application.include_router(
        articles_router,
        prefix=app_settings.api_prefix,
    )

    application.include_router(
        sources_router,
        prefix=app_settings.api_prefix,
    )

    application.include_router(
        digests_router,
        prefix=app_settings.api_prefix,
    )

    application.include_router(
        categories_router,
        prefix=app_settings.api_prefix,
    )

    application.include_router(
        admin_router,
        prefix=app_settings.api_prefix,
    )

    application.include_router(
        users_router,
        prefix=app_settings.api_prefix,
    )

    @application.get("/", tags=["Root"])
    async def root() -> dict[str, str]:
        app_settings = _get_app_settings(application)
        return {
            "message": f"Welcome to {app_settings.app_name}",
            "version": app_settings.app_version,
        }

    return application


app = create_app()
