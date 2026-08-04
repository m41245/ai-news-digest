from enum import StrEnum


class DigestFormat(StrEnum):
    """
    Supported output formats for generated digests.
    """

    HTML = "html"
    MARKDOWN = "markdown"
    PDF = "pdf"
