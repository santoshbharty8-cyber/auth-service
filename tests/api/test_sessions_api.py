from app.models.user_session import UserSession


def test_session_created_on_login(client, db, create_user_and_login):

    user = create_user_and_login(email="session@test.com")

    sessions = db.query(UserSession).all()

    assert len(sessions) == 1
    assert sessions[0].is_active is True


def test_list_sessions(client, create_user_and_login):

    user = create_user_and_login(email="list@test.com")

    response = client.get(
        "/auth/sessions",
        headers=user["headers"]
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_logout_deactivates_session(client, db, create_user_and_login):

    user = create_user_and_login(email="logoutdevice@test.com")

    client.post(
        "/auth/logout",
        json={"refresh_token": user["refresh_token"]},
        headers=user["headers"]
    )

    session = db.query(UserSession).first()

    assert session.is_active is False


def test_refresh_fails_after_logout(client, create_user_and_login):

    user = create_user_and_login(email="refreshfail@test.com")

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


def test_revoke_specific_session(client, create_user_and_login):

    user = create_user_and_login(email="revoke@test.com")

    sessions = client.get(
        "/auth/sessions",
        headers=user["headers"]
    ).json()

    session_id = sessions[0]["id"]

    response = client.delete(
        f"/auth/sessions/{session_id}",
        headers=user["headers"]
    )

    assert response.status_code == 200


def test_force_logout_all_sessions(client, create_user_and_login):

    user = create_user_and_login(email="forceall@test.com")

    client.post(
        "/auth/force-logout-all",
        headers=user["headers"]
    )

    response = client.get(
        "/auth/me",
        headers=user["headers"]
    )

    assert response.status_code == 401