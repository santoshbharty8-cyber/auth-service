import json


def test_oauth_full_login_flow(client, redis_client, monkeypatch):

    state = "test_state"

    from app.api.auth import OAuthHelper

    # ✅ Use real helper (IMPORTANT)
    OAuthHelper.store_state(
        redis_client,
        state,
        {
            "flow": "login",
            "code_verifier": "verifier",
            "created_at": 123456
        }
    )

    monkeypatch.setattr(
        "app.services.auth_service.AuthService.exchange_google_code",
        lambda self, code, verifier: {
            "sub": "google-user-123",
            "email": "test@gmail.com"
        }
    )

    monkeypatch.setattr(
        "app.services.auth_service.AuthService.handle_oauth_login",
        lambda self, payload, ua, ip: {
            "access_token": "token",
            "refresh_token": "refresh"
        }
    )

    response = client.get(
        f"/auth/oauth/google/callback?code=abc&state={state}"
    )

    assert response.status_code == 200