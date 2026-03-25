import pyotp


def test_full_2fa_login_flow(client, real_auth_service, monkeypatch):

    import app.api.auth as auth_module

    # -----------------------------
    # Step 1: Setup user + secret
    # -----------------------------
    user = type("User", (), {"id": "user1", "email": "test@test.com"})()

    secret = "JBSWY3DPEHPK3PXP"  # fixed secret for test

    # mock DB repo
    class FakeCredential:
        def __init__(self):
            self.secret = secret
            self.is_enabled = True

    monkeypatch.setattr(
        auth_module.TOTPRepository,
        "find_by_user",
        lambda self, user_id: FakeCredential()
    )

    # -----------------------------
    # Step 2: MFA challenge
    # -----------------------------
    real_auth_service.mfa_challenge.check_attempts = lambda token: True
    real_auth_service.mfa_challenge.verify_challenge = lambda token: "user1"
    real_auth_service.mfa_challenge.delete_challenge = lambda token: True

    real_auth_service.user_repo.find_by_id = lambda user_id: user

    # -----------------------------
    # Step 3: Generate real TOTP
    # -----------------------------
    totp = pyotp.TOTP(secret)
    code = totp.now()

    # -----------------------------
    # Step 4: Session mock
    # -----------------------------
    real_auth_service.create_session = lambda *args, **kwargs: {
        "access_token": "token",
        "refresh_token": "refresh",
        "token_type": "bearer"
    }

    # -----------------------------
    # Step 5: Call API
    # -----------------------------
    response = client.post(
        "/auth/2fa/login",
        json={
            "mfa_token": "valid_token",
            "code": code
        }
    )

    assert response.status_code == 200
    assert "access_token" in response.json()

def test_2fa_login_invalid_code_flow(client, real_auth_service, monkeypatch):

    import app.api.auth as auth_module

    user = type("User", (), {"id": "user1"})()

    class FakeCredential:
        def __init__(self):
            self.secret = "JBSWY3DPEHPK3PXP"
            self.is_enabled = True

    monkeypatch.setattr(
        auth_module.TOTPRepository,
        "find_by_user",
        lambda self, user_id: FakeCredential()
    )

    real_auth_service.mfa_challenge.check_attempts = lambda token: True
    real_auth_service.mfa_challenge.verify_challenge = lambda token: "user1"

    real_auth_service.user_repo.find_by_id = lambda user_id: user

    response = client.post(
        "/auth/2fa/login",
        json={
            "mfa_token": "valid_token",
            "code": "000000"   # invalid
        }
    )

    assert response.status_code == 401

def test_2fa_invalid_mfa_token_flow(client, real_auth_service):

    real_auth_service.mfa_challenge.check_attempts = lambda token: True
    real_auth_service.mfa_challenge.verify_challenge = lambda token: None

    response = client.post(
        "/auth/2fa/login",
        json={"mfa_token": "invalid", "code": "123456"}
    )

    assert response.status_code == 401

def test_2fa_rate_limit_flow(client, real_auth_service):

    real_auth_service.mfa_challenge.check_attempts = lambda token: False

    response = client.post(
        "/auth/2fa/login",
        json={"mfa_token": "token", "code": "123456"}
    )

    assert response.status_code == 429

def test_2fa_recovery_flow(client, real_auth_service):

    user = type("User", (), {"id": "user1"})()

    real_auth_service.mfa_challenge.check_attempts = lambda token: True
    real_auth_service.mfa_challenge.verify_challenge = lambda token: "user1"
    real_auth_service.mfa_challenge.delete_challenge = lambda token: True

    real_auth_service.user_repo.find_by_id = lambda user_id: user

    # mock recovery success
    from app.services.recovery_code_service import RecoveryCodeService

    RecoveryCodeService.verify_code = lambda self, user_id, code: True

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


