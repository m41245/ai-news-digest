from __future__ import annotations

from typing import Any


class TopicRepository:
    """
    Repository interface for topic entities.
    """

    async def get_by_id(self, topic_id: str) -> Any | None:
        raise NotImplementedError

    async def get_by_slug(self, slug: str) -> Any | None:
        raise NotImplementedError

    async def list_by_ids(self, topic_ids: list[str]) -> list[Any]:
        raise NotImplementedError

    async def list_all(self) -> list[Any]:
        """Return all topics."""
        raise NotImplementedError

    async def list_all_with_counts(self) -> list[Any]:
        """Return all topics with article counts."""
        raise NotImplementedError

    async def create(self, topic: Any) -> Any:
        raise NotImplementedError

    async def create_flush_only(self, topic: Any) -> Any:
        """Persist a topic without committing the session.

        Mirrors :meth:`create` but leaves transaction control to the caller so
        the topic can participate in an outer atomic unit of work.
        """
        raise NotImplementedError

    async def update(self, topic: Any) -> Any:
        raise NotImplementedError

    async def delete(self, topic_id: str) -> None:
        raise NotImplementedError
