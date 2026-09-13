"""
Structured editorial output schemas for M69 intelligent digest generation.

These schemas validate the LLM-generated editorial content and ensure
that only supplied candidate cluster IDs are referenced.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EditorialStory(BaseModel):
    """A single editorial story within a digest."""

    model_config = ConfigDict(frozen=True)

    cluster_id: str = Field(..., min_length=1, max_length=36)
    headline: str = Field(..., min_length=1, max_length=500)
    summary: str = Field(..., min_length=1)
    key_takeaways: tuple[str, ...] = Field(default_factory=tuple)
    why_it_matters: str | None = Field(default=None)

    @field_validator("key_takeaways", mode="before")
    @classmethod
    def _normalize_takeaways(cls, value: Any) -> tuple[str, ...]:
        if value is None:
            return ()
        if isinstance(value, str):
            value = [value]
        items = [str(item).strip() for item in value]
        non_empty = [text for text in items if text]
        if len(non_empty) > 8:
            raise ValueError("key_takeaways must contain at most 8 items.")
        result: list[str] = []
        for text in non_empty:
            if len(text) > 300:
                text = text[:297] + "..."
            result.append(text)
        return tuple(result)

    @field_validator("why_it_matters", mode="before")
    @classmethod
    def _normalize_why(cls, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            raise ValueError("why_it_matters must not be empty.")
        if len(text) > 2000:
            text = text[:1997] + "..."
        return text

    @field_validator("headline", mode="before")
    @classmethod
    def _normalize_headline(cls, value: Any) -> str:
        text = str(value).strip()
        if not text:
            raise ValueError("headline must not be empty.")
        return text[:500]

    @field_validator("summary", mode="before")
    @classmethod
    def _normalize_summary(cls, value: Any) -> str:
        text = str(value).strip()
        if not text:
            raise ValueError("summary must not be empty.")
        if len(text) > 4000:
            text = text[:3997] + "..."
        return text


class EditorialTopStory(EditorialStory):
    """The top story within a digest editorial."""


class EditorialDigestOutput(BaseModel):
    """Structured output produced by the editorial LLM."""

    model_config = ConfigDict(frozen=True)

    title: str = Field(..., min_length=1, max_length=255)
    introduction: str = Field(..., min_length=1)
    top_story: EditorialTopStory | None = None
    stories: tuple[EditorialStory, ...] = Field(default_factory=tuple)

    @field_validator("title", mode="before")
    @classmethod
    def _normalize_title(cls, value: Any) -> str:
        text = str(value).strip()
        if not text:
            raise ValueError("title must not be empty.")
        return text[:255]

    @field_validator("introduction", mode="before")
    @classmethod
    def _normalize_introduction(cls, value: Any) -> str:
        text = str(value).strip()
        if not text:
            raise ValueError("introduction must not be empty.")
        if len(text) > 4000:
            text = text[:3997] + "..."
        return text

    @field_validator("stories", mode="before")
    @classmethod
    def _normalize_stories(cls, value: Any) -> tuple[EditorialStory, ...]:
        if value is None:
            return ()
        if isinstance(value, dict) and "stories" in value:
            value = value["stories"]
        if isinstance(value, list):
            items = []
            seen_ids: set[str] = set()
            for item in value:
                if not isinstance(item, dict):
                    continue
                cid = str(item.get("cluster_id", "")).strip()
                if not cid:
                    continue
                if cid in seen_ids:
                    continue
                seen_ids.add(cid)
                items.append(EditorialStory(**item))
            if len(items) > 20:
                raise ValueError("stories must contain at most 20 items.")
            return tuple(items)
        return ()


def validate_editorial_output(data: dict[str, Any]) -> EditorialDigestOutput:
    """Validate and coerce a raw provider response dict into EditorialDigestOutput.

    Raises ``ValueError`` for irrecoverable validation failures.
    """
    if not isinstance(data, dict):
        raise ValueError("Editorial response must be a JSON object.")

    try:
        return EditorialDigestOutput(**data)
    except Exception as exc:
        raise ValueError(f"Invalid editorial output: {exc}") from exc


__all__ = [
    "EditorialDigestOutput",
    "EditorialStory",
    "EditorialTopStory",
    "validate_editorial_output",
]
