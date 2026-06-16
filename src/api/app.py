from __future__ import annotations

import os

from flask import Flask, jsonify

from src.api.dependencies import init_dependencies
from src.api.middleware.metrics import init_metrics
from src.api.middleware.rate_limiter import init_rate_limiter
from src.api.middleware.security_headers import apply_security_headers
from src.api.routes.health_routes import health_bp
from src.api.routes.news_routes import news_bp
from src.config.logging_config import configure_logging
from src.config.settings import get_settings
from src.config.telemetry import init_tracing


def create_app() -> Flask:
    settings = get_settings()
    configure_logging(settings.ENVIRONMENT)

    # ── Tracing ───────────────────────────────────────────────
    init_tracing(
        service_name=settings.OTEL_SERVICE_NAME,
        service_version=settings.OTEL_SERVICE_VERSION,
        otlp_endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
        environment=settings.ENVIRONMENT,
    )

    # Template folder is relative to this file's directory
    template_dir = os.path.join(os.path.dirname(__file__), "templates")
    app = Flask(__name__, template_folder=template_dir)

    app.secret_key = settings.SECRET_KEY
    app.config["DEBUG"] = settings.DEBUG
    app.config["ENV"] = settings.ENVIRONMENT

    # ── Infrastructure adapters (DB / cache selection) ────────
    init_dependencies()

    # ── Security headers ──────────────────────────────────────
    apply_security_headers(app)

    # ── Rate limiting ─────────────────────────────────────────
    init_rate_limiter(app, max_requests=settings.RATE_LIMIT_PER_MINUTE)

    # ── Prometheus metrics ────────────────────────────────────
    init_metrics(app)

    # ── Blueprints ────────────────────────────────────────────
    app.register_blueprint(news_bp)
    app.register_blueprint(health_bp)

    # ── Error handlers ────────────────────────────────────────
    @app.errorhandler(400)
    def bad_request(exc):
        return jsonify({"error": str(exc.description)}), 400

    @app.errorhandler(404)
    def not_found(exc):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(429)
    def too_many_requests(exc):
        return jsonify({"error": "Rate limit exceeded. Try again later."}), 429

    @app.errorhandler(500)
    def internal_error(exc):
        return jsonify({"error": "Internal server error"}), 500

    return app
