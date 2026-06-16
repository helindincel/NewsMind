from __future__ import annotations

from flask import Blueprint, Response, jsonify
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

health_bp = Blueprint("health", __name__)


@health_bp.route("/health", methods=["GET"])
def health():
    """Liveness + readiness probe."""
    from src.config.telemetry import get_tracer

    tracer = get_tracer("hubb.health")
    with tracer.start_as_current_span("health.check"):
        checks: dict = {}

        # Cache health — import lazily to avoid circular deps
        try:
            from src.api.dependencies import get_cache
            cache = get_cache()
            cache.set("__health__", "ok", ttl=5)
            val = cache.get("__health__")
            checks["cache"] = "ok" if val == "ok" else "error"
        except Exception as exc:
            checks["cache"] = f"error: {exc}"

        status = "healthy" if all(v == "ok" for v in checks.values()) else "degraded"
        http_status = 200 if status == "healthy" else 503

        return jsonify({"status": status, "checks": checks}), http_status


@health_bp.route("/metrics", methods=["GET"])
def metrics():
    """Prometheus metrics scrape endpoint."""
    data = generate_latest()
    return Response(data, status=200, mimetype=CONTENT_TYPE_LATEST)
