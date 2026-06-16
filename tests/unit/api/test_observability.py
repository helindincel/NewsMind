"""Tests for Phase 4 observability: Prometheus metrics and OpenTelemetry tracing."""
from __future__ import annotations

import os
import pytest

os.environ.setdefault("NEWS_API_KEY", "test-key")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("USE_REDIS", "false")


@pytest.fixture(autouse=True)
def reset_deps():
    """Reset DI singletons and tracing state before every test."""
    import src.api.dependencies as deps
    import src.config.telemetry as tel

    deps._article_repo = None
    deps._summary_repo = None
    deps._cache = None
    tel.reset_tracing()
    yield
    tel.reset_tracing()


@pytest.fixture
def app():
    from src.api.app import create_app

    application = create_app()
    application.config["TESTING"] = True
    return application


@pytest.fixture
def client(app):
    return app.test_client()


# ── /metrics endpoint ─────────────────────────────────────────────────────────

class TestMetricsEndpoint:
    def test_metrics_returns_200(self, client):
        resp = client.get("/metrics")
        assert resp.status_code == 200

    def test_metrics_content_type_is_prometheus(self, client):
        resp = client.get("/metrics")
        assert "text/plain" in resp.content_type

    def test_metrics_contains_http_requests_total(self, client):
        # Make a request so the counter has data
        client.get("/health")
        resp = client.get("/metrics")
        body = resp.data.decode()
        assert "http_requests_total" in body

    def test_metrics_contains_duration_histogram(self, client):
        client.get("/health")
        resp = client.get("/metrics")
        body = resp.data.decode()
        assert "http_request_duration_seconds" in body

    def test_metrics_contains_in_flight_gauge(self, client):
        resp = client.get("/metrics")
        body = resp.data.decode()
        assert "http_requests_in_flight" in body


# ── Prometheus middleware ─────────────────────────────────────────────────────

class TestPrometheusMiddleware:
    def test_requests_are_counted(self, client):
        from prometheus_client import REGISTRY

        # Clear metric with known label before test (Prometheus counters accumulate)
        client.get("/health")
        resp = client.get("/metrics")
        body = resp.data.decode()
        # http_requests_total should include GET /health
        assert 'method="GET"' in body

    def test_in_flight_returns_to_zero_after_request(self, client):
        from src.api.middleware.metrics import HTTP_IN_FLIGHT

        before = HTTP_IN_FLIGHT._value.get()
        client.get("/health")
        after = HTTP_IN_FLIGHT._value.get()
        # After a completed request the gauge must return to its prior level
        assert after == before


# ── OpenTelemetry tracing ─────────────────────────────────────────────────────

class TestTelemetryInit:
    def test_init_returns_tracer_provider(self):
        from src.config.telemetry import init_tracing
        from opentelemetry.sdk.trace import TracerProvider

        provider = init_tracing(service_name="test", environment="development")
        assert isinstance(provider, TracerProvider)

    def test_init_is_idempotent(self):
        from src.config.telemetry import init_tracing

        p1 = init_tracing(service_name="test", environment="development")
        p2 = init_tracing(service_name="test", environment="development")
        assert p1 is p2

    def test_get_tracer_returns_tracer(self):
        from src.config.telemetry import get_tracer, init_tracing

        init_tracing(service_name="test", environment="development")
        tracer = get_tracer("hubb.test")
        # Returns a tracer object (exact type varies between real/proxy provider)
        assert tracer is not None

    def test_tracer_creates_spans(self):
        from src.config.telemetry import get_tracer, init_tracing

        init_tracing(service_name="test", environment="development")
        tracer = get_tracer("hubb.test")
        # Spans must be creatable without exceptions
        with tracer.start_as_current_span("test-span") as span:
            assert span is not None

    def test_no_otlp_endpoint_does_not_raise(self):
        """Without OTLP endpoint configured, init should succeed silently."""
        from src.config.telemetry import init_tracing

        provider = init_tracing(
            service_name="test",
            otlp_endpoint=None,
            environment="development",
        )
        assert provider is not None


# ── Logging config (trace ID injection) ──────────────────────────────────────

class TestLoggingConfig:
    def test_configure_logging_development_does_not_raise(self):
        from src.config.logging_config import configure_logging

        configure_logging("development")  # should not raise

    def test_configure_logging_production_does_not_raise(self):
        from src.config.logging_config import configure_logging

        configure_logging("production")  # should not raise

    def test_add_trace_id_without_active_span(self):
        """_add_trace_id should be a no-op when no span is active."""
        from src.config.logging_config import _add_trace_id

        event_dict = {"event": "test"}
        result = _add_trace_id(None, "info", event_dict)
        # Should not raise and should return event_dict unchanged (no trace_id added)
        assert result["event"] == "test"
