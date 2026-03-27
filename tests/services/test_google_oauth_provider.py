import pytest
from types import SimpleNamespace

from fastapi import HTTPException
from app.auth_providers.google_oauth_provider import GoogleOAuthProvider

class FakeUserRepo:
    def __init__(self):
        self.user = None

    def find_by_email(self, email):
        return self.user

    def create(self, user):
        user.id = "user-id"
        return user


class FakeOAuthRepo:
    def __init__(self):
        self.oauth = None

    def find_by_provider_user_id(self, provider, pid):
        return self.oauth

    def create(self, obj):
        self.oauth = obj


def test_authenticate_email_not_verified(monkeypatch):
    provider = GoogleOAuthProvider(FakeUserRepo(), FakeOAuthRepo())

    monkeypatch.setattr(
        provider,
        "exchange_code_for_token",
        lambda c, v: {"id_token": "token"}
    )

    monkeypatch.setattr(
        "app.auth_providers.google_oauth_provider.id_token.verify_oauth2_token",
        lambda *a, **k: {"sub": "1", "email": "a@test.com", "email_verified": False}
    )

    with pytest.raises(HTTPException):
        provider.authenticate("code", "verifier", "login")

def test_authenticate_existing_oauth_user(monkeypatch):
    user = SimpleNamespace(id="u1")

    oauth_repo = FakeOAuthRepo()
    oauth_repo.oauth = SimpleNamespace(user=user)

    provider = GoogleOAuthProvider(FakeUserRepo(), oauth_repo)

    monkeypatch.setattr(provider, "exchange_code_for_token", lambda c, v: {"id_token": "x"})

    monkeypatch.setattr(
        "app.auth_providers.google_oauth_provider.id_token.verify_oauth2_token",
        lambda *a, **k: {"sub": "1", "email": "a@test.com", "email_verified": True}
    )

    result = provider.authenticate("code", "verifier", "login")

    assert result == user

def test_authenticate_link_required(monkeypatch):
    user_repo = FakeUserRepo()
    user_repo.user = SimpleNamespace(id="u1", email="a@test.com")

    provider = GoogleOAuthProvider(user_repo, FakeOAuthRepo())

    monkeypatch.setattr(provider, "exchange_code_for_token", lambda c, v: {"id_token": "x"})

    monkeypatch.setattr(
        "app.auth_providers.google_oauth_provider.id_token.verify_oauth2_token",
        lambda *a, **k: {"sub": "1", "email": "a@test.com", "email_verified": True}
    )

    result = provider.authenticate("code", "verifier", "login")

    assert result["link_required"] is True

def test_authenticate_new_user(monkeypatch):
    user_repo = FakeUserRepo()
    oauth_repo = FakeOAuthRepo()

    provider = GoogleOAuthProvider(user_repo, oauth_repo)

    monkeypatch.setattr(provider, "exchange_code_for_token", lambda c, v: {"id_token": "x"})

    monkeypatch.setattr(
        "app.auth_providers.google_oauth_provider.id_token.verify_oauth2_token",
        lambda *a, **k: {
            "sub": "1",
            "email": "new@test.com",
            "email_verified": True,
            "name": "Test",
            "picture": "pic"
        }
    )

    result = provider.authenticate("code", "verifier", "login")

    assert result.email == "new@test.com"
    assert oauth_repo.oauth is not None

def test_exchange_code_success(monkeypatch):
    provider = GoogleOAuthProvider(FakeUserRepo(), FakeOAuthRepo())

    class FakeResponse:
        status_code = 200
        def json(self):
            return {"id_token": "ok"}

    monkeypatch.setattr(
        "httpx.Client.post",
        lambda *a, **k: FakeResponse()
    )

    result = provider.exchange_code_for_token("c", "v")

    assert result["id_token"] == "ok"

def test_exchange_code_failure(monkeypatch):
    provider = GoogleOAuthProvider(FakeUserRepo(), FakeOAuthRepo())

    class FakeResponse:
        status_code = 400

    monkeypatch.setattr(
        "httpx.Client.post",
        lambda *a, **k: FakeResponse()
    )

    with pytest.raises(HTTPException):
        provider.exchange_code_for_token("c", "v")

def test_verify_identity_success(monkeypatch):
    provider = GoogleOAuthProvider(FakeUserRepo(), FakeOAuthRepo())

    monkeypatch.setattr(
        "app.auth_providers.google_oauth_provider.id_token.verify_oauth2_token",
        lambda *a, **k: {"email_verified": True}
    )

    result = provider.verify_identity("token")

    assert result["email_verified"] is True

def test_verify_identity_failure(monkeypatch):
    provider = GoogleOAuthProvider(FakeUserRepo(), FakeOAuthRepo())

    monkeypatch.setattr(
        "app.auth_providers.google_oauth_provider.id_token.verify_oauth2_token",
        lambda *a, **k: {"email_verified": False}
    )

    with pytest.raises(Exception):
        provider.verify_identity("token")