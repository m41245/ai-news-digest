from __future__ import annotations

from uuid import UUID

from ai_news_digest.domain.models.source import Source
from ai_news_digest.infrastructure.database.models.source_model import (
    SourceModel,
)


class SourceMapper:
    """
    Maps between Source domain objects and SourceModel ORM entities.
    """

    @staticmethod
    def to_model(source: Source) -> SourceModel:
        """
        Convert a domain Source into an ORM SourceModel.
        """
        return SourceModel(
            id=str(source.id),
            name=source.name,
            feed_url=source.feed_url,
            website_url=source.website_url,
            description=source.description,
            is_active=source.is_active,
            created_at=source.created_at,
        )

    @staticmethod
    def to_domain(model: SourceModel) -> Source:
        """
        Convert an ORM SourceModel into a domain Source.
        """
        return Source(
            id=UUID(model.id),
            name=model.name,
            feed_url=model.feed_url,
            website_url=model.website_url,
            description=model.description,
            is_active=model.is_active,
            created_at=model.created_at,
        )

    @staticmethod
    def update_model(
        model: SourceModel,
        source: Source,
    ) -> None:
        """
        Update an existing ORM model from a domain Source.
        """
        model.name = source.name
        model.feed_url = source.feed_url
        model.website_url = source.website_url
        model.description = source.description
        model.is_active = source.is_active
