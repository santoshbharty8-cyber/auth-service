def test_google_login_redirect(client, monkeypatch):

    monkeypatch.setattr(
        "app.services.auth_service.AuthService.start_google_oauth",
        lambda self, flow: "http://google.com/oauth"
    )

    response = client.get(
        "/auth/oauth/google/login",
        follow_redirects=False
        )

    assert response.status_code == 307
    assert "google.com" in response.headers["location"]

def test_invalid_oauth_state(client, monkeypatch):

    monkeypatch.setattr(
        "app.api.auth.OAuthHelper.consume_state",
        lambda redis, state: None
    )

    response = client.get(
        "/auth/oauth/google/callback?code=abc&state=invalid"
    )

    assert response.status_code == 400

def test_google_existing_user_login(
    client,
    mock_oauth_state,
    mock_exchange,
    monkeypatch
):

    monkeypatch.setattr(
        "app.services.auth_service.AuthService.handle_oauth_login",
        lambda self, payload, ua, ip: {
            "access_token": "token",
            "refresh_token": "refresh"
        }
    )

    response = client.get(
        "/auth/oauth/google/callback?code=abc&state=valid"
    )

    assert response.status_code == 200
    assert "access_token" in response.json()

def test_google_link_required(
    client,
    mock_oauth_state,
    mock_exchange,
    monkeypatch
):

    monkeypatch.setattr(
        "app.services.auth_service.AuthService.handle_oauth_login",
        lambda self, payload, ua, ip: {
            "status": "link_required",
            "email": "test@gmail.com"
        }
    )

    response = client.get(
        "/auth/oauth/google/callback?code=abc&state=valid"
    )

    assert response.json()["status"] == "link_required"