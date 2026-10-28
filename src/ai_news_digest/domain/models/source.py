from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlparse
from uuid import UUID, uuid4

from ai_news_digest.domain.enums.source_status import SourceStatus
from ai_news_digest.domain.enums.source_type import SourceType


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
    source_type: SourceType
    status: SourceStatus
    created_at: datetime

    # Trust and source-health metadata.
    publisher: str | None = None
    verification_notes: str | None = None
    priority: int = 0
    last_successful_fetch_at: datetime | None = None
    last_failed_fetch_at: datetime | None = None
    failure_count: int = 0

    @classmethod
    def create(
        cls,
        *,
        name: str,
        feed_url: str,
        website_url: str | None = None,
        description: str | None = None,
        is_active: bool = True,
        source_type: SourceType = SourceType.OTHER,
        status: SourceStatus = SourceStatus.PENDING_REVIEW,
        publisher: str | None = None,
        verification_notes: str | None = None,
        priority: int = 0,
        last_successful_fetch_at: datetime | None = None,
        last_failed_fetch_at: datetime | None = None,
        failure_count: int = 0,
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
            source_type=source_type,
            status=status,
            created_at=datetime.now(UTC),
            publisher=publisher,
            verification_notes=verification_notes,
            priority=priority,
            last_successful_fetch_at=last_successful_fetch_at,
            last_failed_fetch_at=last_failed_fetch_at,
            failure_count=failure_count,
        )

    def update(
        self,
        *,
        name: str | None = None,
        feed_url: str | None = None,
        website_url: str | None = None,
        description: str | None = None,
        is_active: bool | None = None,
        source_type: SourceType | None = None,
        status: SourceStatus | None = None,
        publisher: str | None = None,
        verification_notes: str | None = None,
        priority: int | None = None,
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

        if source_type is not None:
            self.source_type = source_type

        if status is not None:
            self.status = status

        if publisher is not None:
            self.publisher = publisher

        if verification_notes is not None:
            self.verification_notes = verification_notes

        if priority is not None:
            self.priority = priority

    def activate(self) -> None:
        """
        Mark the source as active.
        """
        self.is_active = True

    def deactivate(self) -> None:
        """
        Mark the source as inactive.

        Deactivation disables ingestion eligibility by setting ``is_active`` to
        False while preserving the existing verification status. No new
        SourceStatus value is introduced.
        """
        self.is_active = False

    def is_eligible(self) -> bool:
        """
        Return True when the source is active and verified.

        Only eligible sources may contribute to ingestion and production
        digest generation. Verification status is distinct from general
        editorial reputation: a source is eligible only when it has been
        explicitly verified and has not been disabled.
        """
        return self.is_active and self.status == SourceStatus.VERIFIED

    def record_successful_fetch(self) -> None:
        """
        Record a successful fetch for source-health tracking.

        Resets the consecutive failure count and timestamps the last
        successful fetch. Does not change the verification status.
        """
        self.last_successful_fetch_at = datetime.now(UTC)
        self.failure_count = 0

    def record_failed_fetch(self) -> None:
        """
        Record a failed fetch for source-health tracking.

        Timestamps the last failed fetch and increments the failure count.
        A temporary failure does not automatically revoke verification or
        disable the source; trust state changes are explicit and auditable.
        """
        self.last_failed_fetch_at = datetime.now(UTC)
        self.failure_count += 1

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
