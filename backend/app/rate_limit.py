"""In-memory sliding-window limiter. Fine for one process; use Redis for multiple workers."""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque


class RateLimiter:
    def __init__(self, limit: int, window_seconds: float = 60.0) -> None:
        self.limit, self.window = limit, window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()
        self._calls = 0

    def check(self, key: str, now: float | None = None) -> tuple[bool, int]:
        """Returns (allowed, retry_after_seconds)."""
        now = time.monotonic() if now is None else now
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] >= self.window:
                q.popleft()
            if len(q) >= self.limit:
                return False, max(1, int(self.window - (now - q[0])) + 1)
            q.append(now)
            self._calls += 1
            if self._calls % 1000 == 0:  # prune idle keys so memory stays bounded
                for k in [k for k, v in self._hits.items() if not v or now - v[-1] >= self.window]:
                    del self._hits[k]
            return True, 0
