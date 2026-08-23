from __future__ import annotations

from uuid import UUID

from ai_news_digest.domain.enums.digest_format import DigestFormat
from ai_news_digest.domain.models.digest import Digest
from ai_news_digest.infrastructure.database.models.digest_model import (
    DigestModel,
)


class DigestMapper:
    """
    Maps between Digest domain objects and DigestModel ORM entities.
    """

    @staticmethod
    def to_model(
        digest: Digest,
    ) -> DigestModel:
        """
        Convert a domain Digest into an ORM DigestModel.
        """
        return DigestModel(
            id=str(digest.id),
            title=digest.title,
            content=digest.content,
            format=digest.format,
            generated_at=digest.generated_at,
        )

    @staticmethod
    def to_domain(
        model: DigestModel,
    ) -> Digest:
        """
        Convert an ORM DigestModel into a domain Digest.

        The article_ids are populated from the DigestArticleModel
        relationship if it has been loaded.
        """
        return Digest(
            id=UUID(model.id),
            title=model.title,
            content=model.content,
            generated_at=model.generated_at,
            format=(
                DigestFormat(model.format) if model.format is not None else DigestFormat.MARKDOWN
            ),
            article_ids=[UUID(link.article_id) for link in getattr(model, "digest_articles", [])],
        )

    @staticmethod
    def update_model(
        model: DigestModel,
        digest: Digest,
    ) -> None:
        """
        Update an existing ORM model from a domain Digest.
        """
        model.title = digest.title
        model.content = digest.content
        model.format = digest.format
        model.generated_at = digest.generated_at
