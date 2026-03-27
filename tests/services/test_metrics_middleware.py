import pytest
from types import SimpleNamespace

from app.observability.metrics_middleware import MetricsMiddleware

@pytest.mark.asyncio
async def test_metrics_middleware_success(monkeypatch):

    middleware = MetricsMiddleware(app=None)

    request = SimpleNamespace(
        method="GET",
        url=SimpleNamespace(path="/test")
    )

    class FakeResponse:
        status_code = 200

    async def call_next(req):
        return FakeResponse()

    calls = {"count": False, "latency": False}

    monkeypatch.setattr(
        "app.observability.metrics_middleware.REQUEST_COUNT",
        SimpleNamespace(
            labels=lambda **kwargs: SimpleNamespace(
                inc=lambda: calls.update({"count": True})
            )
        )
    )

    monkeypatch.setattr(
        "app.observability.metrics_middleware.REQUEST_LATENCY",
        SimpleNamespace(
            labels=lambda **kwargs: SimpleNamespace(
                observe=lambda d: calls.update({"latency": True})
            )
        )
    )

    response = await middleware.dispatch(request, call_next)

    assert response.status_code == 200
    assert calls["count"] is True
    assert calls["latency"] is True

@pytest.mark.asyncio
async def test_metrics_middleware_exception(monkeypatch):

    middleware = MetricsMiddleware(app=None)

    request = SimpleNamespace(
        method="POST",
        url=SimpleNamespace(path="/fail")
    )

    async def call_next(req):
        raise Exception("boom")

    calls = {"count": False, "latency": False, "status": None}

    def fake_labels(**kwargs):
        calls["status"] = kwargs.get("status_code")
        return SimpleNamespace(
            inc=lambda: calls.update({"count": True})
        )

    monkeypatch.setattr(
        "app.observability.metrics_middleware.REQUEST_COUNT",
        SimpleNamespace(labels=fake_labels)
    )

    monkeypatch.setattr(
        "app.observability.metrics_middleware.REQUEST_LATENCY",
        SimpleNamespace(
            labels=lambda **kwargs: SimpleNamespace(
                observe=lambda d: calls.update({"latency": True})
            )
        )
    )

    with pytest.raises(Exception):
        await middleware.dispatch(request, call_next)

    # ✅ ensure exception path used status_code=500
    assert calls["status"] == 500

    # ✅ metrics still recorded
    assert calls["count"] is True
    assert calls["latency"] is True

