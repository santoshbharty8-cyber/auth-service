import pytest


@pytest.fixture
def valid_oauth_state():
    return {
        "flow": "login",
        "code_verifier": "test_verifier",
        "user_id": None,
        "created_at": 123456,
    }


@pytest.fixture
def mock_oauth_state(monkeypatch, valid_oauth_state):
    monkeypatch.setattr(
        "app.api.auth.OAuthHelper.consume_state",
        lambda redis, state: valid_oauth_state
    )


@pytest.fixture
def mock_exchange(monkeypatch):
    monkeypatch.setattr(
        "app.services.auth_service.AuthService.exchange_google_code",
        lambda self, code, verifier: {
            "sub": "google-user-123",
            "email": "test@gmail.com"
        }
    )