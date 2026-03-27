import json
import pytest
from types import SimpleNamespace

from app.services.mfa_challenge_service import MFAChallengeService


# ----------------------------------------
# MOCK REDIS
# ----------------------------------------

class DummyRedis:
    def __init__(self):
        self.store = {}
        self.expiry = {}

    def setex(self, key, ttl, value):
        self.store[key] = str(value)

    def get(self, key):
        return self.store.get(key)

    def delete(self, key):
        self.store.pop(key, None)

    def incr(self, key):
        self.store[key] = str(int(self.store.get(key, 0)) + 1)

    def expire(self, key, ttl):
        self.expiry[key] = ttl

    def pipeline(self):
        return self

    def execute(self):
        pass


# ----------------------------------------
# FIXTURE
# ----------------------------------------

@pytest.fixture
def mfa_service(monkeypatch):
    redis = DummyRedis()

    monkeypatch.setattr(
        "app.services.mfa_challenge_service.redis_client",
        redis
    )

    monkeypatch.setattr(
        "app.services.mfa_challenge_service.settings",
        SimpleNamespace(
            MFA_CHALLENGE_TTL=300,
            MFA_MAX_ATTEMPTS=3
        )
    )

    return MFAChallengeService(), redis


# ----------------------------------------
# TEST: create_challenge
# ----------------------------------------

def test_create_challenge(mfa_service):
    svc, redis = mfa_service

    token = svc.create_challenge("user1")

    assert token is not None
    assert redis.get(f"mfa_challenge:{token}") is not None
    assert redis.get(f"mfa_attempts:{token}") == "0"


# ----------------------------------------
# TEST: verify_challenge (success)
# ----------------------------------------

def test_verify_challenge_success(mfa_service):
    svc, redis = mfa_service

    token = svc.create_challenge("user1")

    user_id = svc.verify_challenge(token)

    assert user_id == "user1"


# ----------------------------------------
# TEST: verify_challenge (missing)
# ----------------------------------------

def test_verify_challenge_missing(mfa_service):
    svc, _ = mfa_service

    assert svc.verify_challenge("invalid") is None


# ----------------------------------------
# TEST: delete_challenge
# ----------------------------------------

def test_delete_challenge(mfa_service):
    svc, redis = mfa_service

    token = svc.create_challenge("user1")

    svc.delete_challenge(token)

    assert redis.get(f"mfa_challenge:{token}") is None
    assert redis.get(f"mfa_attempts:{token}") is None


# ----------------------------------------
# TEST: check_attempts (under limit)
# ----------------------------------------

def test_check_attempts_allowed(mfa_service):
    svc, redis = mfa_service

    token = svc.create_challenge("user1")

    redis.store[f"mfa_attempts:{token}"] = "1"

    assert svc.check_attempts(token) is True


# ----------------------------------------
# TEST: check_attempts (blocked)
# ----------------------------------------

def test_check_attempts_blocked(mfa_service):
    svc, redis = mfa_service

    token = svc.create_challenge("user1")

    redis.store[f"mfa_attempts:{token}"] = "3"

    assert svc.check_attempts(token) is False


# ----------------------------------------
# TEST: increment_attempt
# ----------------------------------------

def test_increment_attempt(mfa_service):
    svc, redis = mfa_service

    token = svc.create_challenge("user1")

    svc.increment_attempt(token)

    assert redis.get(f"mfa_attempts:{token}") == "1"
    assert f"mfa_attempts:{token}" in redis.expiry


# ----------------------------------------
# TEST: key helpers
# ----------------------------------------

def test_key_helpers(mfa_service):
    svc, _ = mfa_service

    token = "abc"

    assert svc._key(token) == "mfa_challenge:abc"
    assert svc._attempt_key(token) == "mfa_attempts:abc"