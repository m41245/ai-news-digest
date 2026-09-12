from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class CanonicalCompany:
    """Canonical company entry with normalized name and accepted aliases."""

    name: str
    aliases: tuple[str, ...] = ()


_KNOWN_COMPANIES: tuple[CanonicalCompany, ...] = (
    CanonicalCompany(
        name="OpenAI",
        aliases=("openai", "openai, inc.", "openai's", "openai inc"),
    ),
    CanonicalCompany(
        name="Anthropic",
        aliases=("anthropic", "anthropic ai", "anthropic's"),
    ),
    CanonicalCompany(
        name="Google",
        aliases=("google", "google deepmind", "deepmind", "alphabet"),
    ),
    CanonicalCompany(
        name="Microsoft",
        aliases=("microsoft", "ms", "microsoft corp", "microsoft's"),
    ),
    CanonicalCompany(
        name="Meta",
        aliases=("meta", "meta ai", "facebook", "meta's", "facebook ai"),
    ),
    CanonicalCompany(
        name="NVIDIA",
        aliases=("nvidia", "nvidia corporation", "nvidia's"),
    ),
    CanonicalCompany(
        name="xAI",
        aliases=("xai", "x.ai", "x ai"),
    ),
    CanonicalCompany(
        name="Hugging Face",
        aliases=("hugging face", "huggingface", "hugging face's"),
    ),
    CanonicalCompany(
        name="Mistral",
        aliases=("mistral", "mistral ai", "mistral's"),
    ),
    CanonicalCompany(
        name="DeepMind",
        aliases=("deepmind", "deep mind"),
    ),
)

_ALIAS_MAP: dict[str, str] = {}
_COMPANY_NAME_SET: set[str] = set()

for _entry in _KNOWN_COMPANIES:
    _COMPANY_NAME_SET.add(_entry.name.lower())
    _ALIAS_MAP[_entry.name.lower()] = _entry.name
    for _alias in _entry.aliases:
        _ALIAS_MAP[_alias.lower()] = _entry.name


def normalize_company(raw: str) -> str | None:
    """Return the canonical company name for *raw*, or the cleaned raw value.

    Matching is case-insensitive and tolerant of surrounding whitespace.
    Unknown names are returned as the title-cased cleaned input so callers
    can still persist them if desired.
    """
    cleaned = raw.strip()
    if not cleaned:
        return None
    key = cleaned.lower()
    canonical = _ALIAS_MAP.get(key)
    if canonical is not None:
        return canonical
    if key in _COMPANY_NAME_SET:
        return cleaned
    return cleaned


def is_known_company(raw: str) -> bool:
    """Return ``True`` when *raw* matches a known company or alias."""
    cleaned = raw.strip()
    if not cleaned:
        return False
    key = cleaned.lower()
    return key in _COMPANY_NAME_SET or key in _ALIAS_MAP


__all__ = ["_KNOWN_COMPANIES", "CanonicalCompany", "is_known_company", "normalize_company"]
