from __future__ import annotations

import threading
import time


class RateLimiter:
    """Simple blocking rate limiter: sleeps just enough to respect NCBI's
    documented limit (3 req/s without an API key, 10 req/s with one).
    Applies to any combination of esearch/esummary/efetch/elink calls,
    per NCBI's usage policy."""

    def __init__(self, requests_per_second: float):
        self._min_interval = 1.0 / requests_per_second
        self._lock = threading.Lock()
        self._last_call = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_call
            remaining = self._min_interval - elapsed
            if remaining > 0:
                time.sleep(remaining)
            self._last_call = time.monotonic()
