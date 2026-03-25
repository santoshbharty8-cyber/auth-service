import json
import pytest
from unittest.mock import Mock


@pytest.mark.asyncio
async def test_github_full_login_flow(client, redis_client, monkeypatch):

    from app.api.auth import OAuthHelper

    state = "github_state"

    # ✅ real state storage
    OAuthHelper.store_state(
        redis_client,
        state,
        {
            "flow": "login",
            "code_verifier": "verifier"
        }
    )

    # mock async provider
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
        f"/auth/oauth/github/callback?code=abc&state={state}"
    )

    assert response.status_code == 200