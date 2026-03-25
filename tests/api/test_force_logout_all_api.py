from app.models.user_session import UserSession

def test_force_logout_all(client, create_user_and_login):

    user = create_user_and_login(email="force@test.com")

    # Force logout
    client.post(
        "/auth/force-logout-all",
        headers=user["headers"]
    )

    # Old token should now fail
    response = client.get(
        "/auth/me",
        headers=user["headers"]
    )

    assert response.status_code == 401


def test_force_logout_all_session(client, db, create_user_and_login):

    user = create_user_and_login(email="force@test.com")

    client.post(
        "/auth/force-logout-all",
        headers=user["headers"]
    )

    sessions = db.query(UserSession).all()

    assert all(session.is_active is False for session in sessions)