import uuid
import app.api.auth as auth_module

def test_2fa_setup(client, auth_headers, monkeypatch):

    import app.api.auth as auth_module

    monkeypatch.setattr(
        auth_module.TOTPService,
        "generate_secret",
        lambda self: "secret123"
    )

    monkeypatch.setattr(
        auth_module.TOTPService,
        "build_uri",
        lambda self, email, secret: "otpauth://test"
    )

    monkeypatch.setattr(
        auth_module.TOTPService,
        "generate_qr",
        lambda self, uri: "qr_base64"
    )

    response = client.post("/auth/2fa/setup", headers=auth_headers)

    assert response.status_code == 200
    assert "secret" in response.json()
    assert "qr_code" in response.json()

def test_2fa_verify_not_setup(client, auth_headers):

    response = client.post(
        "/auth/2fa/verify",
        params={"code": "123456"},
        headers=auth_headers
    )

    assert response.status_code == 404

def test_2fa_verify_invalid_code(client, auth_headers, monkeypatch):

    import app.api.auth as auth_module

    # -----------------------------
    # Mock credential exists
    # -----------------------------
    class FakeCredential:
        def __init__(self):
            self.secret = "secret123"

    monkeypatch.setattr(
        auth_module.TOTPRepository,
        "find_by_user",
        lambda self, user_id: FakeCredential()
    )

    # -----------------------------
    # Mock invalid TOTP
    # -----------------------------
    monkeypatch.setattr(
        auth_module.TOTPService,
        "verify",
        lambda *args: False
    )

    response = client.post(
        "/auth/2fa/verify",
        params={"code": "000000"},
        headers=auth_headers
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid code"

def test_2fa_verify_success(client, auth_headers, monkeypatch):

    import app.api.auth as auth_module

    # -----------------------------
    # Mock credential exists
    # -----------------------------
    class FakeCredential:
        def __init__(self):
            self.secret = "secret123"

    monkeypatch.setattr(
        auth_module.TOTPRepository,
        "find_by_user",
        lambda self, user_id: FakeCredential()
    )

    # -----------------------------
    # Mock valid TOTP
    # -----------------------------
    monkeypatch.setattr(
        auth_module.TOTPService,
        "verify",
        lambda *args: True
    )

    # -----------------------------
    # Mock enabling 2FA
    # -----------------------------
    monkeypatch.setattr(
        auth_module.TOTPRepository,
        "enable",
        lambda self, credential: True
    )

    # -----------------------------
    # Mock recovery codes
    # -----------------------------
    monkeypatch.setattr(
        auth_module.RecoveryCodeService,
        "generate_codes",
        lambda *args: ["code1", "code2"]
    )

    response = client.post(
        "/auth/2fa/verify",
        params={"code": "123456"},
        headers=auth_headers
    )

    assert response.status_code == 200
    assert "recovery_codes" in response.json()

def test_2fa_login_rate_limit(client, real_auth_service):

    real_auth_service.mfa_challenge.check_attempts = lambda token: False

    response = client.post(
        "/auth/2fa/login",
        json={"mfa_token": "token", "code": "123456"}
    )

    assert response.status_code == 429

def test_2fa_login_invalid_token(client, real_auth_service):

    real_auth_service.mfa_challenge.check_attempts = lambda token: True
    real_auth_service.mfa_challenge.verify_challenge = lambda token: None

    response = client.post(
        "/auth/2fa/login",
        json={"mfa_token": "token", "code": "123456"}
    )

    assert response.status_code == 401

import uuid

def test_2fa_login_invalid_code(client, real_auth_service, monkeypatch):

    import app.api.auth as auth_module

    # -----------------------------
    # Use UUID (FIX)
    # -----------------------------
    user_id = uuid.uuid4()

    user = type("User", (), {"id": user_id})()

    # -----------------------------
    # MFA challenge
    # -----------------------------
    real_auth_service.mfa_challenge.check_attempts = lambda token: True
    real_auth_service.mfa_challenge.verify_challenge = lambda token: user_id

    real_auth_service.user_repo.find_by_id = lambda uid: user

    # -----------------------------
    # Credential exists
    # -----------------------------
    class FakeCredential:
        def __init__(self):
            self.secret = "secret"
            self.is_enabled = True

    monkeypatch.setattr(
        auth_module.TOTPRepository,
        "find_by_user",
        lambda self, uid: FakeCredential()
    )

    # -----------------------------
    # Invalid TOTP
    # -----------------------------
    monkeypatch.setattr(
        auth_module.TOTPService,
        "verify",
        lambda *args: False
    )

    response = client.post(
        "/auth/2fa/login",
        json={
            "mfa_token": "token",
            "code": "000000"
        }
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid 2FA code"

import uuid

def test_2fa_login_success(client, real_auth_service, monkeypatch):

    import app.api.auth as auth_module

    user_id = uuid.uuid4()
    user = type("User", (), {"id": user_id})()

    # -----------------------------
    # MFA challenge
    # -----------------------------
    real_auth_service.mfa_challenge.check_attempts = lambda token: True
    real_auth_service.mfa_challenge.verify_challenge = lambda token: user_id
    real_auth_service.mfa_challenge.delete_challenge = lambda token: True

    real_auth_service.user_repo.find_by_id = lambda uid: user

    # -----------------------------
    # ✅ FIX: mock credential exists
    # -----------------------------
    class FakeCredential:
        def __init__(self):
            self.secret = "JBSWY3DPEHPK3PXP"
            self.is_enabled = True

    monkeypatch.setattr(
        auth_module.TOTPRepository,
        "find_by_user",
        lambda self, uid: FakeCredential()
    )

    # -----------------------------
    # valid TOTP
    # -----------------------------
    monkeypatch.setattr(
        auth_module.TOTPService,
        "verify",
        lambda *args: True
    )

    # -----------------------------
    # session
    # -----------------------------
    real_auth_service.create_session = lambda *args, **kwargs: {
        "access_token": "token",
        "refresh_token": "refresh",
        "token_type": "bearer"
    }

    # -----------------------------
    # call API
    # -----------------------------
    response = client.post(
        "/auth/2fa/login",
        json={"mfa_token": "token", "code": "123456"}
    )

    assert response.status_code == 200

def test_2fa_recovery_invalid(client, real_auth_service):
    
    user_id = uuid.uuid4()
    user = type("User", (), {"id": user_id})()

    real_auth_service.mfa_challenge.check_attempts = lambda token: True
    real_auth_service.mfa_challenge.verify_challenge = lambda token: user_id

    real_auth_service.user_repo.find_by_id = lambda uid: user

    response = client.post(
        "/auth/2fa/recovery",
        json={"mfa_token": "token", "recovery_code": "wrong"}
    )

    assert response.status_code == 401



def test_2fa_recovery_success(client, real_auth_service, monkeypatch):

    user_id = uuid.uuid4()

    user = type("User", (), {"id": user_id})()

    # MFA
    real_auth_service.mfa_challenge.check_attempts = lambda token: True
    real_auth_service.mfa_challenge.verify_challenge = lambda token: user_id
    real_auth_service.mfa_challenge.delete_challenge = lambda token: True

    real_auth_service.user_repo.find_by_id = lambda uid: user

    # ✅ IMPORTANT: mock recovery service (avoid DB query)
    monkeypatch.setattr(
        auth_module.RecoveryCodeService,
        "verify_code",
        lambda self, uid, code: True
    )

    real_auth_service.create_session = lambda *args, **kwargs: {
        "access_token": "token",
        "refresh_token": "refresh",
        "token_type": "bearer"
    }

    response = client.post(
        "/auth/2fa/recovery",
        json={
            "mfa_token": "token",
            "recovery_code": "valid_code"
        }
    )

    assert response.status_code == 200

def test_generate_recovery_codes(client, auth_headers):

    response = client.post("/auth/2fa/recovery-codes", headers=auth_headers)

    assert response.status_code == 200
    assert "recovery_codes" in response.json()

def test_regenerate_recovery_codes(client, auth_headers):

    response = client.post("/auth/2fa/regenerate-recovery-codes", headers=auth_headers)

    assert response.status_code == 200

