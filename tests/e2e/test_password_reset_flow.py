def test_password_reset_flow(client):

    # --------------------------
    # Register
    # --------------------------
    register = client.post(
        "/auth/register",
        json={
            "email": "reset_e2e@test.com",
            "password": "StrongPass123"
        }
    )

    token = register.json()["verification_token"]

    # --------------------------
    # Verify email
    # --------------------------
    client.post("/auth/verify-email", json={"token": token})

    # --------------------------
    # Request password reset
    # --------------------------
    reset_request = client.post(
        "/auth/password-reset/request",
        json={"email": "reset_e2e@test.com"}
    )

    assert reset_request.status_code == 200

    reset_token = reset_request.json()["reset_token"]

    # --------------------------
    # Confirm reset
    # --------------------------
    confirm = client.post(
        "/auth/password-reset/confirm",
        json={
            "token": reset_token,
            "new_password": "NewStrongPass123"
        }
    )

    assert confirm.status_code == 200

    # --------------------------
    # Login with new password
    # --------------------------
    login = client.post(
        "/auth/login",
        json={
            "email": "reset_e2e@test.com",
            "password": "NewStrongPass123"
        }
    )

    assert login.status_code == 200