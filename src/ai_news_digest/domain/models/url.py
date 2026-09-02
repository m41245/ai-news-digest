from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

_TRACKING_PARAMS: frozenset[str] = frozenset(
    {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "utm_id",
        "utm_source_platform",
        "utm_creative_format",
        "utm_marketing_tactic",
        "fbclid",
        "gclid",
        "dclid",
        "twclid",
        "msclkid",
        "mc_cid",
        "mc_eid",
        "igshid",
        "igsh",
        "ref",
        "ref_src",
        "ref_url",
        "spm",
        "scm",
        "wt_zmc",
        "wtmc",
        "hsa_cam",
        "hsa_grp",
        "hsa_mt",
        "hsa_src",
        "hsa_ad",
        "hsa_acc",
        "hsa_net",
        "hsa_kw",
        "hsa_tgt",
        "hsa_ver",
        "_hsenc",
        "_hsmi",
        "vero_id",
        "vero_conv",
        "yclid",
        "rb_clickid",
        "s_cid",
        "pk_campaign",
        "pk_kwd",
        "pk_keyword",
        "pk_source",
        "pk_medium",
        "pk_content",
        "piwik_campaign",
        "piwik_kwd",
        "mtm_campaign",
        "mtm_keyword",
        "mtm_source",
        "mtm_medium",
        "mtm_content",
        "mtm_cid",
        "mtm_group",
        "mtm_placement",
        "oly_anon_id",
        "oly_enc_id",
    }
)


@dataclass(frozen=True, slots=True)
class CanonicalUrl:
    """
    A normalized, deterministic representation of a resource URL used as the
    article identity boundary for deduplication.

    Canonicalization is intentionally conservative: it removes fragments,
    lowercases the scheme/host, strips a known set of tracking query
    parameters, and removes default ports. It does NOT rewrite hosts,
    resolve redirects, or reorder arbitrary query strings beyond tracking
    removal, so it cannot accidentally collapse distinct resources.
    """

    value: str

    @classmethod
    def parse(cls, raw: str) -> CanonicalUrl:
        """
        Parse and canonicalize a raw URL string.

        Malformed URLs that cannot be parsed at all fall back to the stripped
        input so callers always receive a value. This keeps canonicalization
        total over its input domain while never raising for shape issues.
        """

        cleaned = (raw or "").strip()

        if not cleaned:
            return cls(value="")

        try:
            parsed = urlparse(cleaned)
        except (ValueError, AttributeError):
            return cls(value=cleaned)

        scheme = parsed.scheme.lower()
        netloc = _normalize_netloc(parsed.netloc, scheme)

        path = _normalize_path(parsed.path)

        query = _strip_tracking_params(parsed.query) if parsed.query else ""

        canonical = urlunparse(
            (
                scheme,
                netloc,
                path,
                parsed.params,
                query,
                "",
            )
        )

        return cls(value=canonical)


def _normalize_netloc(netloc: str, scheme: str) -> str:
    """Lowercase host and strip default HTTP/HTTPS ports."""

    if not netloc:
        return netloc

    host = netloc
    port: str | None = None

    if host.startswith("["):
        closing = host.find("]")
        if closing == -1:
            return host.lower()
        body = host[1:closing]
        rest = host[closing + 1 :]
        lower_host = body.lower()
        if rest.startswith(":"):
            port = rest[1:]
    elif ":" in host:
        lower_host, _, port = host.rpartition(":")
        lower_host = lower_host.lower()
    else:
        lower_host = host.lower()
        port = None

    default_port = "80" if scheme == "http" else "443" if scheme == "https" else None

    if port == default_port:
        port = None

    if "@" in lower_host:
        userinfo, _, host_part = lower_host.rpartition("@")
        host_part = host_part.lower()
    else:
        userinfo = ""
        host_part = lower_host

    if port:
        return f"{userinfo}@{host_part}:{port}" if userinfo else f"{host_part}:{port}"

    return f"{userinfo}@{host_part}" if userinfo else host_part


def _normalize_path(path: str) -> str:
    """Normalize '.' and '..' segments and collapse duplicate slashes."""

    if not path:
        return path

    segments: list[str] = []

    for segment in path.split("/"):
        if segment == ".":
            continue
        if segment == "..":
            if segments and segments[-1] != "":
                segments.pop()
            continue
        segments.append(segment)

    normalized = "/".join(segments)

    if path.startswith("/") and not normalized.startswith("/"):
        normalized = "/" + normalized

    return normalized


def _strip_tracking_params(query: str) -> str:
    """Remove known tracking query parameters, preserving the rest in order."""

    try:
        parsed = parse_qs(query, keep_blank_values=True)
    except (ValueError, AttributeError):
        return query

    filtered = [
        (key, values) for key, values in parsed.items() if key.lower() not in _TRACKING_PARAMS
    ]

    if not filtered:
        return ""

    return urlencode(filtered, doseq=True)
