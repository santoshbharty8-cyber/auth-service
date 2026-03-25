import json


def test_oauth_state_reuse_attack(client, redis_client):

    state = "replay_state"

    redis_client.set(
        f"oauth_state:{state}",
        json.dumps({
            "flow": "login",
            "code_verifier": "verifier"
        }),
        ex=300
    )

    # First request
    client.get(f"/auth/oauth/google/callback?code=abc&state={state}")

    # Second request should fail
    response = client.get(
        f"/auth/oauth/google/callback?code=abc&state={state}"
    )

    assert response.status_code == 400

def test_oauth_state_expired(client):

    response = client.get(
        "/auth/oauth/google/callback?code=abc&state=expired"
    )

    assert response.status_code == 400

def test_invalid_pkce(client, redis_client, monkeypatch):

    state = "pkce_test"

    redis_client.set(
        f"oauth_state:{state}",
        json.dumps({
            "flow": "login",
            "code_verifier": "correct_verifier"
        }),
        ex=300
    )

    def mock_exchange(self, code, verifier):
        assert verifier == "correct_verifier"
        raise Exception("PKCE mismatch")

    monkeypatch.setattr(
        "app.services.auth_service.AuthService.exchange_google_code",
        mock_exchange
    )

    response = client.get(
        f"/auth/oauth/google/callback?code=abc&state={state}"
    )
    
    assert response.status_code == 400    
    assert response.json()["detail"] == "Invalid OAuth state"