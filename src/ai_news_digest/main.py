from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from ai_news_digest.api.v1.routes.admin import router as admin_router
from ai_news_digest.api.v1.routes.articles import router as articles_router
from ai_news_digest.api.v1.routes.categories import router as categories_router
from ai_news_digest.api.v1.routes.digests import router as digests_router
from ai_news_digest.api.v1.routes.health import router as health_router
from ai_news_digest.api.v1.routes.sources import router as sources_router
from ai_news_digest.core.config import settings
from ai_news_digest.core.logging import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info(
        "Application starting",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
    )

    yield

    logger.info("Application shutting down")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
    openapi_url=f"{settings.api_prefix}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(health_router)

app.include_router(
    articles_router,
    prefix=settings.api_prefix,
)

app.include_router(
    sources_router,
    prefix=settings.api_prefix,
)

app.include_router(
    digests_router,
    prefix=settings.api_prefix,
)

app.include_router(
    categories_router,
    prefix=settings.api_prefix,
)

app.include_router(
    admin_router,
    prefix=settings.api_prefix,
)


@app.get("/", tags=["Root"])
async def root() -> dict[str, str]:
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
    }


@app.get("/health", tags=["Health"])
async def health() -> dict[str, str]:
    return {
        "status": "healthy",
    }
