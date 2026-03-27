import pytest
from types import SimpleNamespace

from app.auth_providers.otp_provider import OTPAuthProvider


# ----------------------------------------
# FAKE USER REPO
# ----------------------------------------

class FakeUserRepo:
    def __init__(self, user=None):
        self.user = user

    def find_by_email(self, email):
        return self.user


# ----------------------------------------
# TEST: user not found
# ----------------------------------------

def test_authenticate_user_not_found(monkeypatch):
    repo = FakeUserRepo(user=None)
    provider = OTPAuthProvider(repo)

    result = provider.authenticate({
        "email": "test@example.com",
        "otp": "123456",
        "fingerprint": "fp",
        "ip": "127.0.0.1"
    })

    assert result is None


# ----------------------------------------
# TEST: OTP invalid
# ----------------------------------------

def test_authenticate_invalid_otp(monkeypatch):
    user = SimpleNamespace(email="test@example.com")
    repo = FakeUserRepo(user=user)

    provider = OTPAuthProvider(repo)

    monkeypatch.setattr(
        provider.otp_service,
        "verify_otp",
        lambda *args, **kwargs: False
    )

    result = provider.authenticate({
        "email": "test@example.com",
        "otp": "wrong",
        "fingerprint": "fp",
        "ip": "127.0.0.1"
    })

    assert result is None


# ----------------------------------------
# TEST: OTP valid
# ----------------------------------------

def test_authenticate_success(monkeypatch):
    user = SimpleNamespace(email="test@example.com")
    repo = FakeUserRepo(user=user)

    provider = OTPAuthProvider(repo)

    monkeypatch.setattr(
        provider.otp_service,
        "verify_otp",
        lambda *args, **kwargs: True
    )

    result = provider.authenticate({
        "email": "test@example.com",
        "otp": "123456",
        "fingerprint": "fp",
        "ip": "127.0.0.1"
    })

    assert result == user