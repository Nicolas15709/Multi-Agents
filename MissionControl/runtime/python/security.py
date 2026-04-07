"""
Rate limiting + input validation utilities.
Thread-safe, zero external dependencies.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from typing import Optional


# ─── Sliding-window rate limiter ──────────────────────────────────────────────

class RateLimiter:
    """
    Per-key sliding-window rate limiter.
    Thread-safe. Suitable for per-IP limiting in a multithreaded HTTP server.
    """

    def __init__(self, max_requests: int = 60, window_seconds: float = 60.0) -> None:
        self._max = max_requests
        self._window = window_seconds
        self._buckets: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def is_allowed(self, key: str) -> bool:
        """Return True if the request is within limits, False if it should be rejected."""
        now = time.monotonic()
        cutoff = now - self._window
        with self._lock:
            dq = self._buckets[key]
            # Evict timestamps outside the window
            while dq and dq[0] < cutoff:
                dq.popleft()
            if len(dq) >= self._max:
                return False
            dq.append(now)
            return True

    def cleanup_stale(self) -> None:
        """Prune idle buckets to prevent unbounded memory growth (call periodically)."""
        now = time.monotonic()
        cutoff = now - self._window
        with self._lock:
            stale = [k for k, dq in self._buckets.items() if not dq or dq[-1] < cutoff]
            for k in stale:
                del self._buckets[k]


# ─── Input validation ─────────────────────────────────────────────────────────

def validate_str(
    value: object,
    *,
    field: str,
    max_len: int = 500,
    required: bool = False,
) -> str:
    """
    Validate and sanitize a string field from untrusted input.
    Raises ValueError with a machine-readable code on failure.
    """
    if value is None:
        if required:
            raise ValueError(f"{field}_required")
        return ""
    if not isinstance(value, str):
        raise ValueError(f"{field}_must_be_string")
    stripped = value.strip()
    if required and not stripped:
        raise ValueError(f"{field}_required")
    if len(stripped) > max_len:
        raise ValueError(f"{field}_too_long")
    return stripped


def validate_enum(
    value: object,
    *,
    field: str,
    allowed: tuple,
    default: str,
) -> str:
    """Validate that a field is one of the allowed literal values."""
    if value is None:
        return default
    s = validate_str(value, field=field, max_len=64)
    if s not in allowed:
        raise ValueError(f"{field}_invalid_value")
    return s


def validate_bool(value: object, *, field: str, default: bool = False) -> bool:
    """Accept bool or string booleans from JSON payloads."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        if value.lower() in ("1", "true", "yes"):
            return True
        if value.lower() in ("0", "false", "no"):
            return False
    raise ValueError(f"{field}_must_be_boolean")
