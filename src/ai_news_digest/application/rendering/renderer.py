from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from ai_news_digest.domain.enums.digest_format import DigestFormat
from ai_news_digest.domain.models.digest import Digest


@dataclass(frozen=True, slots=True)
class RenderedDigest:
    """Immutable rendered digest output."""

    format: DigestFormat
    content: str | bytes


class DigestRenderer(ABC):
    """Render a Digest into a presentation format without mutating it."""

    @property
    @abstractmethod
    def format(self) -> DigestFormat:
        """The digest format this renderer produces."""

    @abstractmethod
    def render(self, digest: Digest) -> RenderedDigest:
        """Render a Digest into immutable output for the chosen format."""
