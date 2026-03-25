import uuid
from fastapi import HTTPException
from tests.factories.auth_service_factory import create_auth_service

# -----------------------------
# Service-level test
# -----------------------------
def test_magic_link_reuse_service(monkeypatch):

    service = create_auth_service()

    monkeypatch.setattr(
        "app.services.auth_service.verify_magic_link_token",
        lambda token: {
            "jti": str(uuid.uuid4()),
            "sub": uuid.uuid4(),   # ✅ FIXED
            "fingerprint": "fp",
            "ip": "127.0.0.1"
        }
    )

    monkeypatch.setattr(
        "app.services.auth_service.redis_client.set",
        lambda *args, **kwargs: False
    )

    try:
        service.login_with_magic_link("token", "ua", "127.0.0.1")
    except HTTPException as e:
        assert e.status_code == 400


# -----------------------------
# Fingerprint mismatch
# -----------------------------
def test_magic_login_fingerprint_mismatch_service(monkeypatch):

    service = create_auth_service()

    monkeypatch.setattr(
        "app.services.auth_service.verify_magic_link_token",
        lambda token: {
            "jti": str(uuid.uuid4()),
            "sub": str(uuid.uuid4()),
            "fingerprint": "old_fp",
            "ip": "127.0.0.1"
        }
    )

    monkeypatch.setattr(
        "app.services.auth_service.generate_device_fingerprint",
        lambda ua, ip: "new_fp"
    )

    monkeypatch.setattr(
        "app.services.auth_service.redis_client.set",
        lambda *args, **kwargs: True
    )

    monkeypatch.setattr(
        "app.services.auth_service.redis_client.setex",
        lambda *args, **kwargs: True
    )

    result = service.login_with_magic_link("token", "ua", "127.0.0.1")

    assert result["approval_required"] is True