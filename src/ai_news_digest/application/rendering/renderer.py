from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID

from ai_news_digest.domain.enums.digest_format import DigestFormat
from ai_news_digest.domain.models.digest import Digest


@dataclass(frozen=True, slots=True)
class RenderedDigest:
    """Immutable rendered digest output."""

    digest_id: UUID
    format: DigestFormat
    content: str


class DigestRenderer(ABC):
    """Render a Digest into a presentation format without mutating it."""

    @property
    @abstractmethod
    def format(self) -> DigestFormat:
        raise NotImplementedError

    @abstractmethod
    def render(self, digest: Digest) -> RenderedDigest:
        """Render a Digest into immutable output for the chosen format."""
        raise NotImplementedError
