"""
Structured claim/evidence output schemas for M81 evidence-backed intelligence.

These schemas validate LLM-generated claims and their evidence anchors,
ensuring claims are grounded in the supplied article content.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ai_news_digest.domain.enums.claim_type import ClaimType
from ai_news_digest.domain.enums.evidence_type import EvidenceType


class EvidenceAnchorSchema(BaseModel):
    """Schema for a location anchor within article content."""

    model_config = ConfigDict(frozen=True)

    sentence_index: int | None = None
    paragraph_index: int | None = None
    character_start: int | None = None
    character_end: int | None = None
    content_hash: str | None = None


class EvidenceSchema(BaseModel):
    """Schema for a single evidence item supporting a claim."""

    model_config = ConfigDict(frozen=True)

    evidence_type: EvidenceType = Field(default=EvidenceType.ARTICLE_TEXT)
    excerpt: str | None = Field(default=None, max_length=500)
    source_location: str | None = Field(default=None, max_length=256)
    anchor: EvidenceAnchorSchema | None = None

    @field_validator("excerpt", mode="before")
    @classmethod
    def _normalize_excerpt(cls, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        if len(text) > 500:
            text = text[:497] + "..."
        return text


class ClaimSchema(BaseModel):
    """Schema for a single claim extracted from an article."""

    model_config = ConfigDict(frozen=True)

    claim: str = Field(..., min_length=1, max_length=1000)
    type: ClaimType = Field(default=ClaimType.OTHER)
    confidence: float | None = Field(default=None)
    evidence: list[EvidenceSchema] = Field(default_factory=list)

    @field_validator("claim", mode="before")
    @classmethod
    def _normalize_claim(cls, value: Any) -> str:
        text = str(value).strip()
        if not text:
            raise ValueError("claim must not be empty.")
        if len(text) > 1000:
            text = text[:997] + "..."
        return text

    @field_validator("type", mode="before")
    @classmethod
    def _coerce_type(cls, value: Any) -> ClaimType:
        if isinstance(value, ClaimType):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            try:
                return ClaimType(normalized)
            except ValueError:
                return ClaimType.OTHER
        return ClaimType.OTHER

    @field_validator("confidence", mode="before")
    @classmethod
    def _clamp_confidence(cls, value: Any) -> float | None:
        if value is None:
            return None
        try:
            return max(0.0, min(1.0, float(value)))
        except (TypeError, ValueError):
            raise ValueError("confidence must be a number between 0.0 and 1.0.")

    @field_validator("evidence", mode="before")
    @classmethod
    def _normalize_evidence(cls, value: Any) -> list[EvidenceSchema]:
        if value is None:
            return []
        if not isinstance(value, list):
            return []
        result: list[EvidenceSchema] = []
        for item in value:
            if isinstance(item, dict):
                try:
                    result.append(EvidenceSchema(**item))
                except Exception:
                    continue
            elif isinstance(item, EvidenceSchema):
                result.append(item)
        if len(result) > 10:
            result = result[:10]
        return result


class StructuredClaimsOutput(BaseModel):
    """Structured output produced by the claim-extraction LLM."""

    model_config = ConfigDict(frozen=True)

    claims: tuple[ClaimSchema, ...] = Field(default_factory=tuple)

    @field_validator("claims", mode="before")
    @classmethod
    def _normalize_claims(cls, value: Any) -> tuple[ClaimSchema, ...]:
        if value is None:
            return ()
        if isinstance(value, dict) and "claims" in value:
            value = value["claims"]
        if not isinstance(value, list):
            return ()
        seen_texts: set[str] = set()
        result: list[ClaimSchema] = []
        for item in value:
            if isinstance(item, ClaimSchema):
                claim = item
            elif isinstance(item, dict):
                try:
                    claim = ClaimSchema(**item)
                except Exception:
                    continue
            else:
                continue
            normalized_text = claim.claim.strip().lower()
            if normalized_text in seen_texts:
                continue
            seen_texts.add(normalized_text)
            result.append(claim)
            if len(result) >= 20:
                break
        return tuple(result)


def validate_claims_output(data: dict[str, Any]) -> StructuredClaimsOutput:
    """Validate and coerce a raw provider response dict into StructuredClaimsOutput.

    Raises ``ValueError`` for irrecoverable validation failures.
    """
    if not isinstance(data, dict):
        raise ValueError("Claims response must be a JSON object.")
    try:
        return StructuredClaimsOutput(**data)
    except Exception as exc:
        raise ValueError(f"Invalid claims output: {exc}") from exc


__all__ = [
    "ClaimSchema",
    "EvidenceAnchorSchema",
    "EvidenceSchema",
    "StructuredClaimsOutput",
    "validate_claims_output",
]
