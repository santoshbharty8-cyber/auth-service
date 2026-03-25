import app.api.auth as auth_module


# ----------------------------------------
# REQUEST OTP
# ----------------------------------------

def test_request_phone_otp_success(client, monkeypatch):

    # ✅ mock rate limit
    monkeypatch.setattr(
        auth_module.otp_service,
        "rate_limit",
        lambda identifier: True
    )

    # ✅ mock OTP generation
    monkeypatch.setattr(
        auth_module.otp_service,
        "generate_otp",
        lambda *args: "123456"
    )

    # ✅ mock SMS service (IMPORTANT FIX)
    class MockSMS:
        def send_otp(self, phone, otp):
            return None

    monkeypatch.setattr(auth_module, "sms_service", MockSMS())

    response = client.post(
        "/auth/request-phone-otp",
        json={"phone": "+919999999999"}   # ✅ valid E.164 format
    )

    assert response.status_code == 200
    assert response.json()["message"] == "OTP sent successfully"


# ----------------------------------------
# RATE LIMIT
# ----------------------------------------

def test_request_phone_otp_rate_limit(client, monkeypatch):

    monkeypatch.setattr(
        auth_module.otp_service,
        "rate_limit",
        lambda identifier: False
    )

    response = client.post(
        "/auth/request-phone-otp",
        json={"phone": "+919999999999"}   # ✅ valid format
    )

    assert response.status_code == 429
    assert response.json()["detail"] == "Too many OTP requests"


# ----------------------------------------
# INVALID OTP LOGIN
# ----------------------------------------

def test_login_phone_otp_invalid(client, monkeypatch):

    monkeypatch.setattr(
        auth_module.otp_service,
        "verify_otp",
        lambda *args, **kwargs: False
    )

    response = client.post(
        "/auth/login-phone-otp",
        json={
            "phone": "+919999999999",
            "otp": "000000"
        }
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid OTP"


# ----------------------------------------
# LOGIN SUCCESS (EXISTING USER)
# ----------------------------------------

def test_login_phone_otp_success(client, real_auth_service, monkeypatch):

    monkeypatch.setattr(
        auth_module.otp_service,
        "verify_otp",
        lambda *args, **kwargs: True
    )

    # existing user
    real_auth_service.user_repo.find_by_phone = lambda phone: type(
        "User", (), {"id": "1"}
    )()

    real_auth_service.require_2fa = lambda user: False

    real_auth_service.create_session = lambda *args, **kwargs: {
        "access_token": "token",
        "refresh_token": "refresh",
        "token_type": "bearer"
    }

    response = client.post(
        "/auth/login-phone-otp",
        json={
            "phone": "+919999999999",
            "otp": "123456"
        }
    )

    assert response.status_code == 200
    assert "access_token" in response.json()


# ----------------------------------------
# NEW USER FLOW
# ----------------------------------------

def test_login_phone_otp_new_user(client, real_auth_service, monkeypatch):

    monkeypatch.setattr(
        auth_module.otp_service,
        "verify_otp",
        lambda *args, **kwargs: True
    )

    # user not found → create
    real_auth_service.user_repo.find_by_phone = lambda phone: None

    real_auth_service.user_repo.create_phone_user = lambda phone: type(
        "User", (), {"id": "1"}
    )()

    real_auth_service.require_2fa = lambda user: False

    real_auth_service.create_session = lambda *args, **kwargs: {
        "access_token": "token",
        "refresh_token": "refresh",
        "token_type": "bearer"
    }

    response = client.post(
        "/auth/login-phone-otp",
        json={
            "phone": "+919999999999",
            "otp": "123456"
        }
    )

    assert response.status_code == 200


# ----------------------------------------
# 2FA REQUIRED FLOW
# ----------------------------------------

def test_login_phone_otp_requires_2fa(client, real_auth_service, monkeypatch):

    monkeypatch.setattr(
        auth_module.otp_service,
        "verify_otp",
        lambda *args, **kwargs: True
    )

    real_auth_service.user_repo.find_by_phone = lambda phone: type(
        "User", (), {"id": "1"}
    )()

    real_auth_service.require_2fa = lambda user: True

    real_auth_service.mfa_challenge.create_challenge = lambda user_id: "mfa_token"

    response = client.post(
        "/auth/login-phone-otp",
        json={
            "phone": "+919999999999",
            "otp": "123456"
        }
    )

    assert response.status_code == 200
    assert response.json()["require_2fa"] is True


# ----------------------------------------
# VALIDATION TEST (IMPORTANT)
# ----------------------------------------

def test_request_phone_otp_invalid_phone(client):

    response = client.post(
        "/auth/request-phone-otp",
        json={"phone": "9999999999"}   # ❌ invalid format
    )

    assert response.status_code == 422