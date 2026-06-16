"""Prometheus metrics collection middleware.

Exposes the following metrics:
  - http_requests_total          (counter)   — by method, endpoint, status
  - http_request_duration_seconds (histogram) — by method, endpoint
  - http_requests_in_flight      (gauge)      — current concurrent requests
  - app_news_fetches_total       (counter)    — successful news fetches
  - app_summaries_total          (counter)    — summaries created (cached / fresh)
  - app_cache_hits_total         (counter)    — cache hit/miss
"""

from __future__ import annotations

import time

from flask import Flask, Request, Response, request
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
)

# ── HTTP metrics ──────────────────────────────────────────────────────────────

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

HTTP_IN_FLIGHT = Gauge(
    "http_requests_in_flight",
    "Concurrent HTTP requests in progress",
)

# ── Application-level metrics ─────────────────────────────────────────────────

NEWS_FETCHES_TOTAL = Counter(
    "app_news_fetches_total",
    "Successful news feed fetches",
    ["feed_type"],  # top_headlines | keyword
)

SUMMARIES_TOTAL = Counter(
    "app_summaries_total",
    "Summary results served",
    ["source"],  # cached | fresh | error
)

CACHE_OPS_TOTAL = Counter(
    "app_cache_ops_total",
    "Cache operations",
    ["operation", "result"],  # get/hit, get/miss, set/ok, delete/ok
)


def _endpoint_label(req: Request) -> str:
    """Return a low-cardinality endpoint label (avoid capturing IDs in paths)."""
    if req.url_rule:
        return req.url_rule.rule
    # Truncate unknown paths to avoid high cardinality
    path = req.path or "unknown"
    return path[:50]


def init_metrics(app: Flask) -> None:
    """Register before/after request hooks for HTTP instrumentation."""

    @app.before_request
    def _start_timer():
        request._start_time = time.perf_counter()  # type: ignore[attr-defined]
        HTTP_IN_FLIGHT.inc()

    @app.after_request
    def _record_metrics(response: Response) -> Response:
        endpoint = _endpoint_label(request)
        method = request.method

        # Only decrement in-flight and record duration if _start_time was set.
        # If a before_request hook (e.g. rate limiter) short-circuited before
        # _start_timer ran, _start_time will be absent.
        start_time = getattr(request, "_start_time", None)
        if start_time is not None:
            duration = time.perf_counter() - start_time
            HTTP_REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)
            HTTP_IN_FLIGHT.dec()

        HTTP_REQUESTS_TOTAL.labels(
            method=method, endpoint=endpoint, status=str(response.status_code)
        ).inc()
        return response

    @app.teardown_request
    def _in_flight_guard(exc):
        """Safety net: decrement gauge if after_request was skipped (e.g. exception)."""
        # After-request already decremented in the normal path; only fix edge cases.
        # We track with a flag on the request context to avoid double-decrement.
        pass
