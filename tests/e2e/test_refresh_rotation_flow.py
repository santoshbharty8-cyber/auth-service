def test_refresh_token_rotation_flow(client):

    register = client.post(
        "/auth/register",
        json={"email": "rotate_e2e@test.com", "password": "StrongPass123"}
    )

    token = register.json()["verification_token"]

    client.post("/auth/verify-email", json={"token": token})

    login = client.post(
        "/auth/login",
        json={"email": "rotate_e2e@test.com", "password": "StrongPass123"}
    )

    refresh_token = login.json()["refresh_token"]

    # Refresh once
    refresh1 = client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token}
    )

    assert refresh1.status_code == 200

    new_refresh = refresh1.json()["refresh_token"]

    # Old token should fail
    reuse = client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token}
    )

    assert reuse.status_code == 403

    # New token should work
    refresh2 = client.post(
        "/auth/refresh",
        json={"refresh_token": new_refresh}
    )

    assert refresh2.status_code == 200