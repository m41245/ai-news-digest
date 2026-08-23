"""
Factory for creating Source domain entities in tests.
"""

from __future__ import annotations

from ai_news_digest.domain.models.source import Source


def create_source(
    *,
    entity_id: str | None = None,
    name: str = "Test Source",
    feed_url: str = "https://example.com/feed.xml",
    website_url: str | None = None,
    description: str | None = "Test description",
    is_active: bool = True,
) -> Source:
    """
    Create a test Source domain entity.

    Args:
        entity_id: Optional source ID
        name: Source name
        feed_url: RSS feed URL
        website_url: Optional website URL
        description: Optional description
        is_active: Whether the source is active

    Returns:
        Source domain entity
    """
    source = Source.create(
        name=name,
        feed_url=feed_url,
        website_url=website_url,
        description=description,
        is_active=is_active,
    )

    if entity_id is not None:
        object.__setattr__(source, "id", entity_id)
    return source
