from sqlalchemy import text
from datetime import datetime, UTC, timedelta


def test_password_reset_request(client, create_user):

    user = create_user(email="reset@example.com")

    response = client.post(
        "/auth/password-reset/request",
        json={"email": user["email"]}
    )

    assert response.status_code == 200
    assert "message" in response.json()


def test_password_reset_success(client, create_user):

    user = create_user(email="reset2@example.com")

    response = client.post(
        "/auth/password-reset/request",
        json={"email": user["email"]}
    )

    token = response.json()["reset_token"]

    response = client.post(
        "/auth/password-reset/confirm",
        json={
            "token": token,
            "new_password": "NewStrongPass123"
        }
    )

    assert response.status_code == 200


def test_login_after_password_reset(client, create_verified_user):

    user = create_verified_user(email="reset3@example.com")

    response = client.post(
        "/auth/password-reset/request",
        json={"email": user["email"]}
    )

    token = response.json()["reset_token"]

    client.post(
        "/auth/password-reset/confirm",
        json={
            "token": token,
            "new_password": "NewStrongPass123"
        }
    )

    response = client.post(
        "/auth/login",
        json={
            "email": user["email"],
            "password": "NewStrongPass123"
        }
    )

    assert response.status_code == 200


def test_old_password_invalid_after_reset(client, create_verified_user):

    user = create_verified_user(email="reset4@example.com")

    response = client.post(
        "/auth/password-reset/request",
        json={"email": user["email"]}
    )

    token = response.json()["reset_token"]

    client.post(
        "/auth/password-reset/confirm",
        json={
            "token": token,
            "new_password": "NewStrongPass123"
        }
    )

    response = client.post(
        "/auth/login",
        json={
            "email": user["email"],
            "password": "StrongPass123"
        }
    )

    assert response.status_code == 401


def test_password_reset_forces_logout(client, create_user_and_login):

    user = create_user_and_login(email="reset5@example.com")

    response = client.post(
        "/auth/password-reset/request",
        json={"email": user["email"]}
    )

    token = response.json()["reset_token"]

    client.post(
        "/auth/password-reset/confirm",
        json={
            "token": token,
            "new_password": "NewStrongPass123"
        }
    )

    response = client.get(
        "/auth/me",
        headers=user["headers"]
    )

    assert response.status_code == 401


def test_invalid_reset_token(client):

    response = client.post(
        "/auth/password-reset/confirm",
        json={
            "token": "invalid-token",
            "new_password": "Password123"
        }
    )

    assert response.status_code == 400


def test_expired_reset_token(client, db, create_user):

    user = create_user(email="expire@example.com")

    response = client.post(
        "/auth/password-reset/request",
        json={"email": user["email"]}
    )

    token = response.json()["reset_token"]

    db.execute(
        text("UPDATE password_reset_tokens SET expires_at = :time"),
        {"time": datetime.now(UTC) - timedelta(hours=1)}
    )
    db.commit()

    response = client.post(
        "/auth/password-reset/confirm",
        json={
            "token": token,
            "new_password": "Password123"
        }
    )

    assert response.status_code == 400