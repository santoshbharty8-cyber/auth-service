from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from app.core.config import settings


def setup_tracing(app):

    if settings.ENV in ("testing", "development"):
        return

    resource = Resource.create({
        "service.name": "auth-service"
    })

    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)

    exporter = OTLPSpanExporter(
        endpoint=settings.OTEL_EXPORTER_ENDPOINT,
        insecure=True
    )

    span_processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(span_processor)

    FastAPIInstrumentor.instrument_app(app)

    print("Tracing initialized")