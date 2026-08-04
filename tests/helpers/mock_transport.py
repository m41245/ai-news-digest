from __future__ import annotations

from collections.abc import Callable

import httpx


def create_mock_transport(
    handler: Callable[[httpx.Request], httpx.Response],
) -> httpx.MockTransport:
    """
    Create an HTTPX MockTransport.

    This helper allows tests to intercept outgoing HTTP requests
    without performing any real network I/O.

    Parameters
    ----------
    handler:
        Function that receives the outgoing HTTP request and
        returns the desired HTTP response.

    Returns
    -------
    httpx.MockTransport
    """

    return httpx.MockTransport(handler)
