import pytest
from types import SimpleNamespace
from unittest.mock import patch

from app.observability.tracing import setup_tracing


def test_setup_tracing_skips_in_testing(monkeypatch):
    monkeypatch.setattr(
        "app.observability.tracing.settings",
        SimpleNamespace(ENV="testing")
    )

    setup_tracing(app=SimpleNamespace())


def test_setup_tracing_full(monkeypatch):

    calls = {}

    # force production mode
    monkeypatch.setattr(
        "app.observability.tracing.settings",
        SimpleNamespace(
            ENV="production",
            OTEL_EXPORTER_ENDPOINT="http://localhost:4317"
        )
    )

    with patch("opentelemetry.sdk.resources.Resource") as MockResource, \
         patch("opentelemetry.sdk.trace.TracerProvider") as MockProvider, \
         patch("opentelemetry.sdk.trace.export.BatchSpanProcessor") as MockBatch, \
         patch("opentelemetry.exporter.otlp.proto.grpc.trace_exporter.OTLPSpanExporter") as MockExporter, \
         patch("opentelemetry.instrumentation.fastapi.FastAPIInstrumentor") as MockInstr, \
         patch("opentelemetry.trace.set_tracer_provider") as mock_set_provider:

        # configure mocks
        MockResource.create.side_effect = lambda data: calls.update({"resource": data}) or "resource_obj"

        instance_provider = MockProvider.return_value
        instance_provider.add_span_processor.side_effect = lambda sp: calls.update({"span_processor": sp})

        MockExporter.side_effect = lambda **kwargs: calls.update({"exporter": kwargs}) or "exporter_obj"
        MockBatch.side_effect = lambda exporter: calls.update({"batch": exporter}) or "batch_obj"
        MockInstr.instrument_app.side_effect = lambda app: calls.update({"instrumented": True})

        # run
        setup_tracing(app=SimpleNamespace())

        # assertions
        assert calls["resource"]["service.name"] == "auth-service"
        assert calls["instrumented"] is True