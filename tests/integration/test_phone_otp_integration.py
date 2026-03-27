from types import SimpleNamespace
from app.services.sms_service import SMSService

def test_full_phone_otp_flow(client, real_auth_service, monkeypatch):

    import app.api.auth as auth_module

    # -----------------------------
    # Capture OTP instead of sending SMS
    # -----------------------------
    captured = {}

    class MockSMS:
        def send_otp(self, phone, otp):
            captured["otp"] = otp

    monkeypatch.setattr(auth_module, "sms_service", MockSMS())

    # -----------------------------
    # Step 1: Request OTP
    # -----------------------------
    response = client.post(
        "/auth/request-phone-otp",
        json={"phone": "+919999999999"}   # ✅ FIXED
    )

    assert response.status_code == 200

    # ensure OTP captured
    assert "otp" in captured

    # -----------------------------
    # Setup service behavior
    # -----------------------------
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

    # -----------------------------
    # Step 2: Login using OTP
    # -----------------------------
    response = client.post(
        "/auth/login-phone-otp",
        json={
            "phone": "+919999999999",   # ✅ FIXED
            "otp": captured["otp"]      # ✅ REAL OTP
        }
    )

    assert response.status_code == 200
    assert "access_token" in response.json()


def test_send_otp_success(monkeypatch):

    # 🔥 fake Twilio message response
    fake_message = SimpleNamespace(sid="SM123")

    class FakeMessages:
        def create(self, **kwargs):
            # assert payload correctness (important)
            assert "Your verification code is" in kwargs["body"]
            assert kwargs["to"] == "+1234567890"
            return fake_message

    class FakeClient:
        def __init__(self, *args, **kwargs):
            self.messages = FakeMessages()

    # ✅ patch Twilio Client
    monkeypatch.setattr(
        "app.services.sms_service.Client",
        FakeClient
    )

    # optional: patch settings
    monkeypatch.setattr(
        "app.services.sms_service.settings",
        SimpleNamespace(
            TWILIO_ACCOUNT_SID="sid",
            TWILIO_AUTH_TOKEN="token",
            TWILIO_PHONE_NUMBER="+1000000000"
        )
    )

    service = SMSService()

    result = service.send_otp("+1234567890", "123456")

    assert result == "SM123"