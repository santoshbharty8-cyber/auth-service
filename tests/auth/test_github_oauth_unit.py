import pytest
from unittest.mock import Mock
from fastapi import HTTPException

def test_github_login_redirect(client, monkeypatch):

    monkeypatch.setattr(
        "app.services.auth_service.AuthService.start_github_oauth",
        lambda self, flow: "http://github.com/oauth"
    )

    response = client.get(
        "/auth/oauth/github/login",
        follow_redirects=False
    )

    assert response.status_code == 307
    assert "github.com" in response.headers["location"]

def test_github_invalid_state(client, monkeypatch):

    monkeypatch.setattr(
        "app.api.auth.OAuthHelper.consume_state",
        lambda redis, state: None
    )

    response = client.get(
        "/auth/oauth/github/callback?code=abc&state=invalid"
    )

    assert response.status_code == 400



@pytest.mark.asyncio
async def test_github_existing_user_login(client, monkeypatch):

    # mock state
    monkeypatch.setattr(
        "app.api.auth.OAuthHelper.consume_state",
        lambda redis, state: {
            "flow": "login",
            "code_verifier": "verifier"
        }
    )

    # mock provider
    async def mock_exchange(self, code, verifier):
        return "token"

    async def mock_user(self, token):
        return {"id": 123, "name": "test"}

    async def mock_email(self, token):
        return "test@gmail.com"

    monkeypatch.setattr(
        "app.auth_providers.github_oauth_provider.GitHubOAuthProvider.exchange_code",
        mock_exchange
    )
    monkeypatch.setattr(
        "app.auth_providers.github_oauth_provider.GitHubOAuthProvider.fetch_user",
        mock_user
    )
    monkeypatch.setattr(
        "app.auth_providers.github_oauth_provider.GitHubOAuthProvider.fetch_email",
        mock_email
    )

    # mock service
    monkeypatch.setattr(
        "app.services.auth_service.AuthService.handle_github_oauth_login",
        lambda self, provider, payload: Mock(id=1)
    )

    monkeypatch.setattr(
        "app.services.auth_service.AuthService.create_session",
        lambda self, user, user_agent, ip_address: {
            "access_token": "token"
        }
    )

    response = client.get(
        "/auth/oauth/github/callback?code=abc&state=valid"
    )

    assert response.status_code == 200

def test_github_account_exists_conflict(client, monkeypatch):

    # ✅ mock state
    monkeypatch.setattr(
        "app.api.auth.OAuthHelper.consume_state",
        lambda redis, state: {
            "flow": "login",
            "code_verifier": "verifier"
        }
    )

    # ✅ mock async provider methods (IMPORTANT)
    async def mock_exchange(self, code, verifier):
        return "fake_token"

    async def mock_user(self, token):
        return {"id": 123, "name": "test"}

    async def mock_email(self, token):
        return "test@gmail.com"

    monkeypatch.setattr(
        "app.auth_providers.github_oauth_provider.GitHubOAuthProvider.exchange_code",
        mock_exchange
    )
    monkeypatch.setattr(
        "app.auth_providers.github_oauth_provider.GitHubOAuthProvider.fetch_user",
        mock_user
    )
    monkeypatch.setattr(
        "app.auth_providers.github_oauth_provider.GitHubOAuthProvider.fetch_email",
        mock_email
    )

    # ✅ mock service conflict
    def mock_login(self, provider, payload):
        raise HTTPException(
            status_code=409,
            detail="Account exists. Please link GitHub."
        )

    monkeypatch.setattr(
        "app.services.auth_service.AuthService.handle_github_oauth_login",
        mock_login
    )

    response = client.get(
        "/auth/oauth/github/callback?code=abc&state=valid"
    )

    assert response.status_code == 409