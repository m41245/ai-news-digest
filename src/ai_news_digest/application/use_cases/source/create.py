from __future__ import annotations

from typing import TYPE_CHECKING

from ai_news_digest.application.dto.source import (
    CreateSourceRequest,
    SourceResponse,
)
from ai_news_digest.application.exceptions.source import (
    SourceAlreadyExistsError,
)
from ai_news_digest.domain.models.source import Source

if TYPE_CHECKING:
    from ai_news_digest.domain.ports.source_repository import SourceRepository


class CreateSourceUseCase:
    """
    Application use case responsible for creating a news source.
    """

    def __init__(
        self,
        repository: SourceRepository,
    ) -> None:
        self._repository = repository

    async def execute(
        self,
        request: CreateSourceRequest,
    ) -> SourceResponse:
        """
        Create a new news source.
        """

        existing = await self._repository.get_by_feed_url(
            request.feed_url,
        )

        if existing is not None:
            raise SourceAlreadyExistsError(
                request.feed_url,
            )

        source = Source.create(
            name=request.name,
            feed_url=request.feed_url,
            website_url=request.website_url,
            description=request.description,
            is_active=request.is_active,
        )

        created = await self._repository.create(source)

        return SourceResponse(
            id=str(created.id),
            name=created.name,
            feed_url=created.feed_url,
            website_url=created.website_url,
            description=created.description,
            is_active=created.is_active,
        )
