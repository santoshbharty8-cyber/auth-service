import pytest
from app.security.rate_limiter import SlidingWindowRateLimiter


def test_rate_limiter_allows_requests(monkeypatch):

    limiter = SlidingWindowRateLimiter(
        prefix="test",
        max_requests=5,
        window_seconds=60
    )

    monkeypatch.setattr(
        "app.security.rate_limiter.redis_client.eval",
        lambda *args, **kwargs: 1
    )

    count, _, limit, _ = limiter.check("user1")

    assert count <= limit


def test_rate_limiter_blocks_after_limit(monkeypatch):

    limiter = SlidingWindowRateLimiter(
        prefix="test",
        max_requests=5,
        window_seconds=60
    )

    monkeypatch.setattr(
        "app.security.rate_limiter.redis_client.eval",
        lambda *args, **kwargs: 6
    )

    count, _, limit, _ = limiter.check("user1")

    assert count >= limit


def test_rate_limiter_isolated_keys(monkeypatch):

    limiter = SlidingWindowRateLimiter(
        prefix="test",
        max_requests=5,
        window_seconds=60
    )

    calls = []

    def fake_eval(script, numkeys, key, *args):
        calls.append(key)
        return 1

    monkeypatch.setattr(
        "app.security.rate_limiter.redis_client.eval",
        fake_eval
    )

    limiter.check("user1")
    limiter.check("user2")

    assert len(calls) == 2


def test_rate_limiter_window_reset(monkeypatch):

    limiter = SlidingWindowRateLimiter(
        prefix="test",
        max_requests=2,
        window_seconds=1
    )

    responses = [1, 2, 1]

    def fake_eval(*args, **kwargs):
        return responses.pop(0)

    monkeypatch.setattr(
        "app.security.rate_limiter.redis_client.eval",
        fake_eval
    )

    limiter.check("user1")
    limiter.check("user1")

    count, _, _, _ = limiter.check("user1")

    assert count == 1