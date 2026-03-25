import pytest
from app.api.auth import OAuthHelper


@pytest.mark.asyncio
async def test_github_state_reuse(client, redis_client, monkeypatch):


    state = "replay_state"

    OAuthHelper.store_state(
        redis_client,
        state,
        {"flow": "login", "code_verifier": "verifier"}
    )

    # ✅ MOCK PROVIDER (IMPORTANT)
    async def mock_exchange(self, code, verifier):
        return "token"

    async def mock_user(self, token):
        return {"id": 123}

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

    # first call (valid)
    client.get(f"/auth/oauth/github/callback?code=abc&state={state}")

    # second call (should fail)
    response = client.get(
        f"/auth/oauth/github/callback?code=abc&state={state}"
    )

    assert response.status_code == 400

@pytest.mark.asyncio
async def test_github_invalid_pkce(client, redis_client, monkeypatch):

    state = "pkce_test"

    OAuthHelper.store_state(
        redis_client,
        state,
        {"flow": "login", "code_verifier": "correct"}
    )

    async def mock_exchange(self, code, verifier):
        raise Exception("Invalid PKCE")

    monkeypatch.setattr(
        "app.auth_providers.github_oauth_provider.GitHubOAuthProvider.exchange_code",
        mock_exchange
    )

    response = client.get(
        f"/auth/oauth/github/callback?code=abc&state={state}"
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid OAuth credentials"

