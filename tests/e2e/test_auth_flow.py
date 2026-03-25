def test_full_authentication_flow(client):

    # --------------------------
    # 1 Register
    # --------------------------
    register = client.post(
        "/auth/register",
        json={
            "email": "e2e@test.com",
            "password": "StrongPass123"
        }
    )

    assert register.status_code == 200
    verification_token = register.json()["verification_token"]

    # --------------------------
    # 2 Verify Email
    # --------------------------
    verify = client.post(
        "/auth/verify-email",
        json={"token": verification_token}
    )

    assert verify.status_code == 200

    # --------------------------
    # 3 Login
    # --------------------------
    login = client.post(
        "/auth/login",
        json={
            "email": "e2e@test.com",
            "password": "StrongPass123"
        }
    )

    assert login.status_code == 200

    tokens = login.json()

    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    # --------------------------
    # 4 Access Protected Route
    # --------------------------
    me = client.get("/auth/me", headers=headers)

    assert me.status_code == 200
    assert me.json()["email"] == "e2e@test.com"

    # --------------------------
    # 5 Refresh Token
    # --------------------------
    refresh = client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token}
    )

    assert refresh.status_code == 200
    new_token = refresh.json()
    new_access = new_token["access_token"]
    new_refresh = new_token["refresh_token"]

    headers = {
        "Authorization": f"Bearer {new_access}"
    }

    # --------------------------
    # 6 List Sessions
    # --------------------------
    sessions = client.get(
        "/auth/sessions",
        headers=headers
    )

    assert sessions.status_code == 200
    assert len(sessions.json()) == 1

    # --------------------------
    # 7 Logout
    # --------------------------
    logout = client.post(
        "/auth/logout",
        json={"refresh_token": new_refresh},
        headers=headers
    )

    assert logout.status_code == 200

    # --------------------------
    # 8 Token should be revoked
    # --------------------------
    after_logout = client.get(
        "/auth/me",
        headers=headers
    )

    assert after_logout.status_code == 401