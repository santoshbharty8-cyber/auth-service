from app.models.user_session import UserSession


def test_session_management_flow(client, db):

    # --------------------------
    # Register
    # --------------------------
    register = client.post(
        "/auth/register",
        json={
            "email": "session_e2e@test.com",
            "password": "StrongPass123"
        }
    )

    verification_token = register.json()["verification_token"]

    # --------------------------
    # Verify email
    # --------------------------
    client.post(
        "/auth/verify-email",
        json={"token": verification_token}
    )

    # --------------------------
    # Login
    # --------------------------
    login = client.post(
        "/auth/login",
        json={
            "email": "session_e2e@test.com",
            "password": "StrongPass123"
        }
    )

    assert login.status_code == 200

    refresh_token = login.json()["refresh_token"]
    access_token = login.json()["access_token"]

    # --------------------------
    # Verify session created in DB
    # --------------------------
    session = db.query(UserSession).first()

    assert session is not None
    assert session.is_active is True

    # --------------------------
    # Logout
    # --------------------------
    client.post(
        "/auth/logout",
        json={"refresh_token": refresh_token},
        headers={"Authorization": f"Bearer {access_token}"}
    )

    # --------------------------
    # Verify session revoked in DB
    # --------------------------
    db.refresh(session)

    assert session.is_active is False