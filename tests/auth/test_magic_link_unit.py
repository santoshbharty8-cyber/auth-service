
def test_request_magic_link_success(client, mock_auth_service):

    response = client.post(
        "/auth/magic-link",
        params={"email": "test@gmail.com"}
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Magic login link sent"



def test_request_magic_link_user_not_found(client, mock_auth_service):

    response = client.post(
        "/auth/magic-link",
        params={"email": "unknown@gmail.com"}
    )

    assert response.status_code == 200

    
def test_magic_login_trusted_device(client, mock_auth_service):

    mock_auth_service.login_with_magic_link.return_value = {
        "access_token": "token"
    }

    response = client.get("/auth/magic-login?token=test")

    assert response.status_code == 200
    assert "access_token" in response.json()
    
def test_magic_link_replay_attack(client, mock_auth_service):

    from fastapi import HTTPException

    mock_auth_service.login_with_magic_link.side_effect = HTTPException(
        status_code=400,
        detail="Magic link already used"
    )

    response = client.get("/auth/magic-login?token=test")

    assert response.status_code == 400

def test_magic_login_requires_approval(client, mock_auth_service):

    mock_auth_service.login_with_magic_link.return_value = {
        "approval_required": True,
        "approval_link": "link"
    }

    response = client.get("/auth/magic-login?token=test")

    assert response.status_code == 200
    assert response.json()["approval_required"] is True