import pytest
from app.main import app

@pytest.fixture(autouse=True)
def enable_rate_limit():

    app.state.rate_limit_disabled = False

def test_login_rate_limit(client, create_verified_user):

    user = create_verified_user(email=None)

    responses = []

    for _ in range(6):

        r = client.post(
            "/auth/login",
            json={
                "email": user["email"],
                "password": "wrongpassword"
            }
        )

        responses.append(r.status_code)
    print(responses)
    
    assert responses[-1] == 429

def test_register_rate_limit(client):

    responses = []

    for i in range(102):

        r = client.post(
            "/auth/register",
            json={
                "email": f"user{i}@test.com",
                "password": "StrongPass123"
            }
        )

        responses.append(r.status_code)
    print(responses)
    assert responses[-1] == 429

def test_ip_rate_limit(client):

    responses = []

    for i in range(1100):

        r = client.get("/docs")

        responses.append(r.status_code)

    assert responses[-1] == 429