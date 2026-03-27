import pytest
from types import SimpleNamespace

from app.core import health_checks


# ----------------------------------------
# TEST: check_database SUCCESS
# ----------------------------------------

def test_check_database_success(monkeypatch):
    
    class DummyConn:
        def execute(self, query):
            return 1

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    class DummyEngine:
        def begin(self):
            return DummyConn()

    monkeypatch.setattr(
        health_checks,
        "engine",
        DummyEngine()
    )

    assert health_checks.check_database() is True


# ----------------------------------------
# TEST: check_database FAILURE
# ----------------------------------------

def test_check_database_failure(monkeypatch):

    class DummyEngine:
        def begin(self):
            raise Exception("DB down")

    monkeypatch.setattr(
        health_checks,
        "engine",
        DummyEngine()
    )

    assert health_checks.check_database() is False


# ----------------------------------------
# TEST: check_redis SUCCESS
# ----------------------------------------

def test_check_redis_success(monkeypatch):

    monkeypatch.setattr(
        health_checks,
        "redis_client",
        SimpleNamespace(ping=lambda: True)
    )

    assert health_checks.check_redis() is True


# ----------------------------------------
# TEST: check_redis FAILURE
# ----------------------------------------

def test_check_redis_failure(monkeypatch):

    def broken_ping():
        raise Exception("Redis down")

    monkeypatch.setattr(
        health_checks,
        "redis_client",
        SimpleNamespace(ping=broken_ping)
    )

    assert health_checks.check_redis() is False