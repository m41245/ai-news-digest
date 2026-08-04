from functools import lru_cache

from ai_news_digest.core.config import Settings, get_settings


@lru_cache(maxsize=1)
def get_app_settings() -> Settings:
    """
    Dependency provider for application settings.

    This wrapper allows FastAPI dependencies to access
    the cached Settings instance while keeping the
    implementation centralized.
    """
    return get_settings()
