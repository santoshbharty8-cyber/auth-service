import json
import uuid
from types import SimpleNamespace


def test_magic_login_full_flow(client, real_auth_service, monkeypatch):

    monkeypatch.setattr(
        "app.services.auth_service.verify_magic_link_token",
        lambda token: {
            "jti": str(uuid.uuid4()),
            "sub": str(uuid.uuid4()),   # must be string
            "fingerprint": "fp",
            "ip": "127.0.0.1"
        }
    )

    monkeypatch.setattr(
        "app.services.auth_service.generate_device_fingerprint",
        lambda ua, ip: "fp"
    )

    monkeypatch.setattr(
        "app.services.auth_service.redis_client.set",
        lambda *args, **kwargs: True
    )

    real_auth_service.device_repo.find_device = lambda *args: True

    real_auth_service.create_session = lambda *args, **kwargs: {
        "access_token": "token"
    }

    response = client.get("/auth/magic-login?token=test")

    assert response.status_code == 200


def test_approve_login_success(client, real_auth_service, redis_client, monkeypatch):

    user = SimpleNamespace(id="123")

    # ✅ FIX: return valid user
    monkeypatch.setattr(
        real_auth_service.user_repo,
        "find_by_id",
        lambda uid: user
    )

    real_auth_service.require_2fa = lambda user: False

    real_auth_service.create_session = lambda *args, **kwargs: {
        "access_token": "token"
    }

    real_auth_service.device_repo.create_device = lambda *args, **kwargs: True

    request_id = "req123"

    redis_client.set(
        f"login_approval:{request_id}",
        json.dumps({
            "user_id": "123",
            "fingerprint": "fp",
            "ip": "127.0.0.1"
        })
    )

    response = client.get(f"/auth/approve-login?request_id={request_id}")

    assert response.status_code == 200
    assert response.json()["access_token"] == "token"
    
def test_approve_login_invalid(client):

    response = client.get("/auth/approve-login?request_id=invalid")

    assert response.status_code == 400