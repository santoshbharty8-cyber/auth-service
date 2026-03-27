import pytest
from types import SimpleNamespace

from app.observability.request_logging_middleware import RequestLoggingMiddleware

@pytest.mark.asyncio
async def test_request_logging_success(monkeypatch):

    middleware = RequestLoggingMiddleware(app=None)

    request = SimpleNamespace(
        method="GET",
        url=SimpleNamespace(path="/test"),
        state=SimpleNamespace(request_id="req1", user_id="u1"),
        client=SimpleNamespace(host="127.0.0.1"),
    )

    class FakeResponse:
        status_code = 200

    async def call_next(req):
        return FakeResponse()

    calls = {}

    monkeypatch.setattr(
        "app.observability.request_logging_middleware.logger.info",
        lambda msg, extra: calls.update(extra)
    )

    response = await middleware.dispatch(request, call_next)

    assert response.status_code == 200
    assert calls["event"] == "request_completed"
    assert calls["status_code"] == 200

@pytest.mark.asyncio
async def test_request_logging_exception(monkeypatch):

    middleware = RequestLoggingMiddleware(app=None)

    request = SimpleNamespace(
        method="POST",
        url=SimpleNamespace(path="/fail"),
        state=SimpleNamespace(request_id="req2"),
        client=None,
    )

    async def call_next(req):
        raise Exception("boom")

    calls = {}

    monkeypatch.setattr(
        "app.observability.request_logging_middleware.logger.exception",
        lambda msg, extra: calls.update(extra)
    )

    with pytest.raises(Exception):
        await middleware.dispatch(request, call_next)

    # ✅ verify exception logging
    assert calls["event"] == "request_failed"
    assert calls["method"] == "POST"
    assert calls["path"] == "/fail"

