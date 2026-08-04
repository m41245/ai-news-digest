from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

if TYPE_CHECKING:
    from ai_news_digest.domain.enums.digest_format import DigestFormat


@dataclass(slots=True)
class Digest:
    """
    Represents a generated news digest within the domain layer.
    """

    id: UUID
    title: str
    content: str
    generated_at: datetime
    format: DigestFormat
    article_ids: list[UUID] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        *,
        title: str,
        content: str,
        digest_format: DigestFormat,
        article_ids: list[UUID] | None = None,
    ) -> Digest:
        """
        Factory method for creating a generated digest.
        """
        return cls(
            id=uuid4(),
            title=title,
            content=content,
            generated_at=datetime.now(UTC),
            format=digest_format,
            article_ids=article_ids or [],
        )
