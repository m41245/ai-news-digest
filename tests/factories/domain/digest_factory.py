"""
Factory for creating Digest domain entities in tests.
"""

from __future__ import annotations

from uuid import UUID

from ai_news_digest.domain.enums.digest_format import DigestFormat
from ai_news_digest.domain.models.digest import Digest


def create_digest(
    *,
    entity_id: str | None = None,
    title: str = "Test Digest",
    content: str = "Test digest content",
    digest_format: DigestFormat = DigestFormat.MARKDOWN,
    article_ids: list[UUID] | None = None,
) -> Digest:
    """
    Create a test Digest domain entity.

    Args:
        entity_id: Optional digest ID
        title: Digest title
        content: Digest content
        digest_format: Digest format
        article_ids: List of article IDs

    Returns:
        Digest domain entity
    """
    if article_ids is None:
        article_ids = []

    digest = Digest.create(
        title=title,
        content=content,
        digest_format=digest_format,
        article_ids=article_ids,
    )

    if entity_id is not None:
        object.__setattr__(digest, "id", entity_id)

    return digest
