from __future__ import annotations

from enum import StrEnum


class EntityType(StrEnum):
    """Supported entity types for knowledge graph nodes."""

    COMPANY = "company"
    TOPIC = "topic"
    STORY = "story"
    ARTICLE = "article"


__all__ = ["EntityType"]
