"""OpenTelemetry tracing initialisation.

Supports two modes:
- Local (default): OTLP exporter disabled; traces logged to console at DEBUG level.
- Production: Set OTEL_EXPORTER_OTLP_ENDPOINT to send spans to any OTLP-compatible
  collector (Jaeger, Grafana Tempo, etc.).
"""
from __future__ import annotations

import logging

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)

logger = logging.getLogger(__name__)

_tracer_provider: TracerProvider | None = None


def init_tracing(
    service_name: str = "hubb-api",
    service_version: str = "1.0.0",
    otlp_endpoint: str | None = None,
    environment: str = "development",
) -> TracerProvider:
    """Initialise and register the global TracerProvider.

    Call once from :func:`create_app`.  Subsequent calls are no-ops so the
    provider is only ever configured once per process.
    """
    global _tracer_provider
    if _tracer_provider is not None:
        return _tracer_provider

    resource = Resource.create(
        {
            SERVICE_NAME: service_name,
            SERVICE_VERSION: service_version,
            "deployment.environment": environment,
        }
    )

    provider = TracerProvider(resource=resource)

    if otlp_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )

            exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
            provider.add_span_processor(BatchSpanProcessor(exporter))
            logger.info("tracing.otlp_exporter_enabled", extra={"endpoint": otlp_endpoint})
        except Exception as exc:
            logger.warning("tracing.otlp_exporter_failed: %s — falling back to console", exc)
            provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    elif environment == "development":
        # Console exporter is noisy; only add when DEBUG logging is on
        if logging.getLogger().isEnabledFor(logging.DEBUG):
            provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(provider)
    _tracer_provider = provider
    logger.info("tracing.initialised service=%s env=%s", service_name, environment)
    return provider


def get_tracer(name: str = "hubb") -> trace.Tracer:
    """Return a tracer bound to the configured provider."""
    return trace.get_tracer(name)


def reset_tracing() -> None:
    """Reset global state — only used in tests.

    We only reset the module-level singleton so `init_tracing` can be called
    again.  We intentionally do NOT override the OTel global provider here
    because ``ProxyTracerProvider()`` creates an infinite recursion in
    opentelemetry 1.x when you chain proxies.
    """
    global _tracer_provider
    _tracer_provider = None
