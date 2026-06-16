from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock

from flask import Flask, Request, Response, abort, request


class RateLimiter:
    """
    In-memory sliding-window rate limiter (per IP).
    Thread-safe. No external dependency — works without Redis.

    Phase 3: swap this for a Redis-backed implementation so
    limits are shared across all Gunicorn workers.
    """

    def __init__(self, max_requests: int = 60, window_seconds: int = 60) -> None:
        self._max = max_requests
        self._window = window_seconds
        # {ip: [(timestamp, count), ...]}
        self._buckets: dict[str, list] = defaultdict(list)
        self._lock = Lock()

    def is_allowed(self, ip: str) -> tuple[bool, int]:
        """
        Returns (allowed, requests_remaining).
        """
        now = time.monotonic()
        cutoff = now - self._window

        with self._lock:
            # Drop expired entries
            self._buckets[ip] = [ts for ts in self._buckets[ip] if ts > cutoff]
            count = len(self._buckets[ip])
            if count >= self._max:
                return False, 0
            self._buckets[ip].append(now)
            return True, self._max - count - 1


_limiter: RateLimiter | None = None


def init_rate_limiter(app: Flask, max_requests: int = 60) -> None:
    global _limiter
    _limiter = RateLimiter(max_requests=max_requests, window_seconds=60)

    @app.before_request
    def _check_rate_limit() -> Response | None:
        if _limiter is None:
            return None

        # Health & metrics endpoints are exempt
        if request.path in ("/health", "/metrics"):
            return None

        ip = _get_client_ip(request)
        allowed, remaining = _limiter.is_allowed(ip)

        if not allowed:
            abort(429)

        return None

    @app.after_request
    def _add_rate_limit_headers(response: Response) -> Response:
        if _limiter is not None:
            ip = _get_client_ip(request)
            _, remaining = (
                _limiter.is_allowed.__func__(  # type: ignore[attr-defined]
                    _limiter, ip
                )
                if False
                else (True, 0)
            )
            response.headers["X-RateLimit-Limit"] = str(_limiter._max)
        return response


def _get_client_ip(req: Request) -> str:
    """
    Safely extract the real client IP.
    X-Forwarded-For is only trusted when behind a known proxy (e.g. nginx).
    For local development, use remote_addr directly.
    """
    forwarded_for = req.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the leftmost (original client) IP
        return forwarded_for.split(",")[0].strip()
    return req.remote_addr or "unknown"
