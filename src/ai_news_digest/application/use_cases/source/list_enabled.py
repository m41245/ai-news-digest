from __future__ import annotations

from typing import TYPE_CHECKING

from ai_news_digest.application.dto.source import SourceResponse

if TYPE_CHECKING:
    from ai_news_digest.domain.ports.source_repository import SourceRepository


class ListEnabledSourcesUseCase:
    """
    Application use case responsible for retrieving all enabled news sources.
    """

    def __init__(
        self,
        repository: SourceRepository,
    ) -> None:
        self._repository = repository

    async def execute(
        self,
    ) -> list[SourceResponse]:
        """
        Retrieve all enabled news sources ordered by name.
        """

        sources = await self._repository.list_enabled()

        return [
            SourceResponse(
                id=str(source.id),
                name=source.name,
                feed_url=source.feed_url,
                website_url=source.website_url,
                description=source.description,
                is_active=source.is_active,
            )
            for source in sources
        ]
