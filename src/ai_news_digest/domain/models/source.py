from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlparse
from uuid import UUID, uuid4


@dataclass(slots=True)
class Source:
    """
    Domain entity representing an RSS/news source.

    The entity owns its business state and exposes behavior through
    domain methods instead of allowing callers to manipulate attributes
    directly.
    """

    id: UUID
    name: str
    feed_url: str
    website_url: str | None
    description: str | None
    is_active: bool
    created_at: datetime

    @classmethod
    def create(
        cls,
        *,
        name: str,
        feed_url: str,
        website_url: str | None = None,
        description: str | None = None,
        is_active: bool = True,
    ) -> Source:
        """
        Factory method for creating a new news source.
        """
        cls.validate_feed_url(feed_url)

        return cls(
            id=uuid4(),
            name=name,
            feed_url=feed_url,
            website_url=website_url,
            description=description,
            is_active=is_active,
            created_at=datetime.now(UTC),
        )

    def update(
        self,
        *,
        name: str | None = None,
        feed_url: str | None = None,
        website_url: str | None = None,
        description: str | None = None,
        is_active: bool | None = None,
    ) -> None:
        """
        Update the source using partial values.

        Only values explicitly provided are modified.
        """
        if feed_url is not None:
            self.validate_feed_url(feed_url)

        if name is not None:
            self.name = name

        if feed_url is not None:
            self.feed_url = feed_url

        if website_url is not None:
            self.website_url = website_url

        if description is not None:
            self.description = description

        if is_active is not None:
            self.is_active = is_active

    def activate(self) -> None:
        """
        Mark the source as active.
        """
        self.is_active = True

    def deactivate(self) -> None:
        """
        Mark the source as inactive.
        """
        self.is_active = False

    @classmethod
    def validate(cls, source: Source) -> None:
        """
        Validate the source domain object.

        Raises ValueError if any business rule is violated.
        """
        cls.validate_feed_url(source.feed_url)

    @staticmethod
    def validate_feed_url(feed_url: str) -> None:
        """
        Validate the feed_url format.

        Raises ValueError if the URL is malformed or uses an unsupported scheme.
        """
        parsed = urlparse(feed_url)

        if not parsed.scheme:
            raise ValueError("feed_url must include a scheme (http or https).")

        if parsed.scheme not in {"http", "https"}:
            raise ValueError("feed_url scheme must be http or https.")

        if not parsed.netloc:
            raise ValueError("feed_url must include a valid host.")
