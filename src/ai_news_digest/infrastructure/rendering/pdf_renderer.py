from __future__ import annotations

from ai_news_digest.application.rendering.renderer import DigestRenderer, RenderedDigest
from ai_news_digest.domain.enums.digest_format import DigestFormat
from ai_news_digest.domain.models.digest import Digest


class PDFRenderer(DigestRenderer):
    """Placeholder contract for future PDF rendering support.

    This intentionally does not import PDF generation libraries or perform any
    rendering work. It defines the required interface boundary for future PDF
    implementation without coupling the application layer to a concrete library.
    """

    @property
    def format(self) -> DigestFormat:
        return DigestFormat.PDF

    def render(self, digest: Digest) -> RenderedDigest:
        raise NotImplementedError(
            "PDF rendering is not implemented yet; this is a placeholder contract."
        )
