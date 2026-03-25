from app.models import User

def test_login_success(client, create_verified_user):

    user = create_verified_user(email="login@example.com")

    response = client.post(
        "/auth/login",
        json={
            "email": user["email"],
            "password": user["password"]
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert "access_token" in data
    assert "refresh_token" in data

def test_login_wrong_password(client, create_verified_user):

    user = create_verified_user(email="wrong@example.com")

    response = client.post(
        "/auth/login",
        json={
            "email": user["email"],
            "password": "WrongPass"
        }
    )

    assert response.status_code == 401

def test_password_is_hashed(db, create_user):

    result = create_user()
    print(result)
    db.expire_all()
    user = db.query(User).filter_by(email=result["email"]).first()
    print(user)

    assert user is not None
    assert user.password_hash.startswith("$argon2")

def test_failed_attempt_increment(client, db, create_verified_user):

    user = create_verified_user(email="fail@test.com")

    client.post(
        "/auth/login",
        json={
            "email": user["email"],
            "password": "WrongPass"
        }
    )

    db_user = db.query(User).filter_by(email=user["email"]).first()

    assert db_user.failed_attempts == 1

def test_account_lock(client, create_verified_user):

    user = create_verified_user(email="lock@test.com")

    for _ in range(5):
        client.post(
            "/auth/login",
            json={
                "email": user["email"],
                "password": "wrongPass123"
            }
        )

    response = client.post(
        "/auth/login",
        json={
            "email": user["email"],
            "password": "wrongPass123"
        }
    )

    assert response.status_code == 403

def test_reset_failed_attempts(client, db, create_verified_user):

    user = create_verified_user(email="reset@test.com")

    client.post(
        "/auth/login",
        json={
            "email": user["email"],
            "password": "WrongPass"
        }
    )

    client.post(
        "/auth/login",
        json={
            "email": user["email"],
            "password": user["password"]
        }
    )

    db_user = db.query(User).filter_by(email=user["email"]).first()

    assert db_user.failed_attempts == 0

def test_refresh_success(client, create_user_and_login):

    user = create_user_and_login(email="refresh@test.com")

    response = client.post(
        "/auth/refresh",
        json={"refresh_token": user["refresh_token"]}
    )

    assert response.status_code == 200
    assert "access_token" in response.json()

def test_refresh_rotation(client, create_user_and_login):

    user = create_user_and_login(email="rotate@test.com")

    old_refresh = user["refresh_token"]

    client.post(
        "/auth/refresh",
        json={"refresh_token": old_refresh}
    )

    reuse = client.post(
        "/auth/refresh",
        json={"refresh_token": old_refresh}
    )

    assert reuse.status_code == 403

def test_logout_success(client, create_user_and_login):

    user = create_user_and_login(email="logout@test.com")

    response = client.post(
        "/auth/logout",
        json={"refresh_token": user["refresh_token"]},
        headers=user["headers"]
    )

    assert response.status_code == 200

def test_refresh_after_logout_fails(client, create_user_and_login):

    user = create_user_and_login(email="logout2@test.com")

    client.post(
        "/auth/logout",
        json={"refresh_token": user["refresh_token"]},
        headers=user["headers"]
    )

    response = client.post(
        "/auth/refresh",
        json={"refresh_token": user["refresh_token"]}
    )

    assert response.status_code == 403

def test_protected_route_success(client, create_user_and_login):

    user = create_user_and_login(email="secure@test.com")

    response = client.get(
        "/auth/me",
        headers=user["headers"]
    )

    assert response.status_code == 200
    assert response.json()["email"] == user["email"]

def test_protected_route_without_token(client):

    response = client.get("/auth/me")

    assert response.status_code in (401, 403)

def test_protected_route_invalid_token(client):

    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalidtoken"}
    )

    assert response.status_code == 401

def test_admin_route_forbidden(client, create_user_and_login):

    user = create_user_and_login(email="user@test.com")

    response = client.get(
        "/admin",
        headers=user["headers"]
    )

    assert response.status_code == 403
