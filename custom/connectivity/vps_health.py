"""
VPS health check — Fase 3.

Synchronous HTTP GET to {vps_url}/health.
Returns True if the endpoint responds with 2xx within the timeout.
Called from the hot path (every chat turn), so the timeout is short.
"""

import urllib.request
import urllib.error


_TIMEOUT_S = 3


class VpsHealthCheck:
    """Connectivity oracle consumed by LumiAgent."""

    def __init__(self, vps_url: str) -> None:
        # Normalise: strip trailing slash, append /health
        base = vps_url.rstrip("/")
        # If base_url includes a path prefix (e.g. /v1), check one level up.
        self._health_url = f"{base}/health"

    def is_online(self) -> bool:
        try:
            with urllib.request.urlopen(self._health_url, timeout=_TIMEOUT_S) as resp:
                return resp.status < 300
        except Exception:
            return False
