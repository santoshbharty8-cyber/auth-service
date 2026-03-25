import pytest
from app.main import app

@pytest.fixture(autouse=True)
def enable_rate_limit():

    app.state.rate_limit_disabled = False

def test_user_rate_limit(client, create_user_and_login):

    user = create_user_and_login(email=None)

    responses = []

    for _ in range(120):

        r = client.get(
            "/auth/me",
            headers=user["headers"]
        )

        responses.append(r.status_code)

    assert responses[-1] == 429

def test_rate_limit_headers(client, create_verified_user):

    user = create_verified_user(email=None)

    for _ in range(6):
        response = client.post(
            "/auth/login",
            json={
                "email": user["email"],
                "password": user["password"]
            }
        )

    assert response.status_code == 429
    assert "X-RateLimit-Limit" in response.headers
    assert "X-RateLimit-Window" in response.headers