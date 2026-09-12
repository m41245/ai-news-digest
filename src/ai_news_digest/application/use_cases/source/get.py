from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from ai_news_digest.application.dto.source import SourceResponse
from ai_news_digest.application.exceptions.source import (
    SourceNotFoundError,
)

if TYPE_CHECKING:
    from ai_news_digest.domain.ports.source_repository import SourceRepository


class GetSourceUseCase:
    """
    Application use case responsible for retrieving a news source.
    """

    def __init__(
        self,
        repository: SourceRepository,
    ) -> None:
        self._repository = repository

    async def execute(
        self,
        source_id: UUID,
    ) -> SourceResponse:
        """
        Retrieve a source by its identifier.
        """

        source = await self._repository.get_by_id(source_id)

        if source is None:
            raise SourceNotFoundError(
                str(source_id),
            )

        return SourceResponse(
            id=str(source.id),
            name=source.name,
            feed_url=source.feed_url,
            website_url=source.website_url,
            description=source.description,
            is_active=source.is_active,
            status=source.status.value,
        )
