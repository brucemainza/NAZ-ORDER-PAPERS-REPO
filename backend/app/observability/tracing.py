import logging

logger = logging.getLogger(__name__)


def configure_tracing(app, settings) -> bool:
    if not settings.otel_enabled:
        return False
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError as error:  # pragma: no cover - packaging guard
        raise RuntimeError("OpenTelemetry is enabled but dependencies are missing") from error

    provider = TracerProvider(
        resource=Resource.create({"service.name": settings.otel_service_name})
    )
    exporter_options = {}
    if settings.otel_exporter_otlp_endpoint:
        exporter_options["endpoint"] = settings.otel_exporter_otlp_endpoint
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(**exporter_options)))
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=provider,
        excluded_urls="/livez,/readyz,/health,/metrics",
        exclude_spans=["receive", "send"],
    )
    logger.info("OpenTelemetry tracing enabled")
    return True
