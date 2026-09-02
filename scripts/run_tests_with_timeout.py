"""Run pytest with a hard wall-clock timeout (Windows-safe helper).

Usage:
    poetry run python scripts/run_tests_with_timeout.py [pytest args...]
"""

from __future__ import annotations

import subprocess
import sys
import threading

TIMEOUT_SECONDS = 1200

_proc: subprocess.Popen[bytes] | None = None


def _kill_on_timeout() -> None:  # pragma: no cover
    print(f"\n[timeout-helper] Hard timeout reached after {TIMEOUT_SECONDS}s.", file=sys.stderr)
    if _proc is not None and _proc.poll() is None:
        _proc.kill()


def main() -> int:
    args = ["pytest", "-p", "no:cacheprovider"]
    args.extend(sys.argv[1:])

    global _proc
    timer = threading.Timer(TIMEOUT_SECONDS, _kill_on_timeout)
    timer.daemon = True
    timer.start()

    try:
        _proc = subprocess.Popen(args)  # noqa: S603
        _proc.communicate()
    finally:
        timer.cancel()

    return int(_proc.returncode or 1)


if __name__ == "__main__":
    raise SystemExit(main())
