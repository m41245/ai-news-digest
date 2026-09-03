"""Classify values in local env files as placeholder vs real, without printing values.

Output only key names and value lengths/classifications; never prints secrets.
"""

from __future__ import annotations


def _looks_placeholder(value: str) -> bool:
    lowered = value.strip().lower()
    if not lowered:
        return True
    if lowered in {
        "true",
        "false",
        "utc",
        "0.1.0",
        "ai news digest",
        "production",
        "development",
        "staging",
        "testing",
    }:
        return True
    placeholder_markers = (
        "your_",
        "change-me",
        "change_me",
        "changeme",
        "changeme-to-a-secure",
        "replace-me",
        "replace_me",
        "please-replace",
        "example.com",
        "localhost",
        "<redacted>",
        "placeholder",
        "test-secret-key",
        "insecure",
        "dev-secret-key",
        "secret",
        "password",
        "12345678901234567890123456789012",
    )
    return any(marker in lowered for marker in placeholder_markers) or (
        all(c in "0123456789abcdef" for c in lowered)
        and ("0123456789abcdef" in lowered or "abcdef0123456789" in lowered)
    )


def scan(path: str) -> None:
    from pathlib import Path

    print(f"{path}: {'present' if Path(path).exists() else 'MISSING'}")
    if not Path(path).exists():
        return
    with Path(path).open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            classification = "REAL-VALUE" if not _looks_placeholder(value) else "placeholder"
            print(f"  [{classification:11s}] {key}  value_length={len(value)}")


if __name__ == "__main__":
    for env_file in (".env", ".env.prod.local"):
        scan(env_file)
