"""
Public-facing API response schemas.

These schemas intentionally expose a restricted, enriched view of articles,
digests and categories suitable for unauthenticated consumption. Internal
fields (raw article content, internal IDs, processing details) are omitted or
replaced with human-friendly values.
"""

from __future__ import annotations

from pydantic import BaseModel


class PublicArticleResponse(BaseModel):
    """Public view of an article, enriched with source and category names."""

    id: str
    title: str
    url: str
    summary: str | None = None
    status: str
    published_at: str | None = None
    source_name: str | None = None
    category_name: str | None = None


class PublicDigestResponse(BaseModel):
    """Public view of a digest."""

    id: str
    title: str
    content: str
    format: str
    generated_at: str
    article_count: int


class PublicCategoryResponse(BaseModel):
    """Public view of a category."""

    id: str
    name: str
    description: str | None = None


__all__ = [
    "PublicArticleResponse",
    "PublicCategoryResponse",
    "PublicDigestResponse",
]
