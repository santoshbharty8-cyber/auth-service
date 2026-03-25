from app.security.jwt import decode_access_token
from app.cache.redis_client import redis_client


def test_access_token_blacklist(client, create_user_and_login):

    user = create_user_and_login(email="black@test.com")

    access_token = user["access_token"]
    refresh_token = user["refresh_token"]

    # Decode token to get JTI
    payload = decode_access_token(access_token)
    token_jti = payload["jti"]

    # Logout (this should blacklist the access token)
    client.post(
        "/auth/logout",
        json={"refresh_token": refresh_token},
        headers=user["headers"]
    )

    # Try accessing protected route
    response = client.get(
        "/auth/me",
        headers=user["headers"]
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Token has been revoked"
    
    # Verify token stored in blacklist
    assert redis_client.exists(f"blacklist:{token_jti}")
    assert redis_client.get(f"blacklist:{token_jti}") == "revoked"