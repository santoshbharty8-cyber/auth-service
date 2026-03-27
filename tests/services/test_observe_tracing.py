import pytest
from types import SimpleNamespace

from app.observability.tracing import setup_tracing

def test_setup_tracing_skips_in_testing(monkeypatch):

    monkeypatch.setattr(
        "app.observability.tracing.settings",
        SimpleNamespace(ENV="testing")
    )

    # should NOT raise or do anything
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

    # mock Resource
    monkeypatch.setattr(
        "app.observability.tracing.Resource.create",
        lambda data: calls.update({"resource": data}) or "resource_obj"
    )

    # mock TracerProvider
    class FakeProvider:
        def __init__(self, resource=None):
            calls["provider_resource"] = resource

        def add_span_processor(self, sp):
            calls["span_processor"] = sp

    monkeypatch.setattr(
        "app.observability.tracing.TracerProvider",
        FakeProvider
    )

    # mock trace.set_tracer_provider
    monkeypatch.setattr(
        "app.observability.tracing.trace.set_tracer_provider",
        lambda p: calls.update({"set_provider": True})
    )

    # mock exporter
    monkeypatch.setattr(
        "app.observability.tracing.OTLPSpanExporter",
        lambda **kwargs: calls.update({"exporter": kwargs}) or "exporter_obj"
    )

    # mock span processor
    monkeypatch.setattr(
        "app.observability.tracing.BatchSpanProcessor",
        lambda exporter: calls.update({"batch": exporter}) or "batch_obj"
    )

    # mock FastAPI instrumentor
    monkeypatch.setattr(
        "app.observability.tracing.FastAPIInstrumentor.instrument_app",
        lambda app: calls.update({"instrumented": True})
    )

    # run
    setup_tracing(app=SimpleNamespace())

    # assertions
    assert calls["resource"]["service.name"] == "auth-service"
    assert calls["set_provider"] is True
    assert calls["instrumented"] is True

