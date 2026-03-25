import uuid
import app.api.webauthn_router as router_module
from app.dependencies.services import get_webauthn_service
from app.dependencies.auth_dependencies import get_auth_service

def test_webauthn_start_login_success(client, override_dep, monkeypatch):
    
    class FakeUser:
        def __init__(self):
            self.id = uuid.uuid4()
            self.email = "test@test.com"

    class FakeUserRepo:
        def __init__(self, db):
            pass

        def find_by_email(self, email):
            return FakeUser()

    monkeypatch.setattr(router_module, "UserRepository", FakeUserRepo)

    # -----------------------------
    # Mock WebAuthn Service
    # -----------------------------
    class MockService:
        def start_login(self, user):
            return {"publicKey": {"challenge": "abc"}}

    override_dep(get_webauthn_service, lambda: MockService())

    # -----------------------------
    # CALL API
    # -----------------------------
    response = client.post(
        "/webauthn/login/start",
        json={"email": "test@test.com"}
    )

    assert response.status_code == 200
    assert "publicKey" in response.json()

def test_webauthn_start_login_user_not_found(client, monkeypatch):

    monkeypatch.setattr(
        "app.api.webauthn_router.UserRepository.find_by_email",
        lambda self, email: None
    )

    response = client.post(
        "/webauthn/login/start",
        json={"email": "unknown@test.com"}
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"

def test_webauthn_start_login_no_credentials(client, monkeypatch):

    class FakeUser:
        def __init__(self):
            import uuid
            self.id = uuid.uuid4()
            self.email = "test@test.com"

    monkeypatch.setattr(
        "app.api.webauthn_router.UserRepository.find_by_email",
        lambda self, email: FakeUser()
    )

    # service throws exception
    def raise_error(user):
        raise Exception("No passkeys registered")

    monkeypatch.setattr(
        "app.api.webauthn_router.get_webauthn_service",
        lambda: type("S", (), {"start_login": raise_error})()
    )

    response = client.post(
        "/webauthn/login/start",
        json={"email": "test@test.com"}
    )

    assert response.status_code == 500

def test_webauthn_finish_login_invalid(client, override_dep):

    class MockWebAuthn:
        def finish_login(self, credential):
            return None

    # -----------------------------
    # Mock AuthService (won’t be used, but MUST override)
    # -----------------------------
    class MockAuth:
        def create_session(self, *args, **kwargs):
            return {"access_token": "token"}

    override_dep(get_webauthn_service, lambda: MockWebAuthn())
    override_dep(get_auth_service, lambda: MockAuth())

    response = client.post(
        "/webauthn/login/finish",
        json={"id": "cred123"}
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid passkey authentication"

def test_webauthn_finish_login_validation_error(client, override_dep):

    class MockWebAuthn:
        def finish_login(self, credential):
            raise ValueError("Invalid signature")

    # -----------------------------
    # Mock AuthService (required)
    # -----------------------------
    class MockAuth:
        def create_session(self, *args, **kwargs):
            return {"access_token": "token"}

    override_dep(get_webauthn_service, lambda: MockWebAuthn())
    override_dep(get_auth_service, lambda: MockAuth())

    response = client.post(
        "/webauthn/login/finish",
        json={"id": "cred123"}
    )

    assert response.status_code == 400
    assert "Invalid signature" in response.json()["detail"]

def test_webauthn_finish_login_success(client, override_dep):

    user = type(
        "User",
        (),
        {
            "id": uuid.uuid4(),
            "email": "test@test.com",   # ✅ REQUIRED
            "is_active": True           # ✅ SAFE ADD
        }
    )()

    # -----------------------------
    # Mock WebAuthn
    # -----------------------------
    class MockWebAuthn:
        def finish_login(self, credential):
            return user

    # -----------------------------
    # Mock AuthService
    # -----------------------------
    class MockAuth:
        def create_session(self, user, user_agent=None, ip_address=None):
            return {
                "access_token": "token",
                "refresh_token": "refresh",
                "token_type": "bearer"
            }

    override_dep(get_webauthn_service, lambda: MockWebAuthn())
    override_dep(get_auth_service, lambda: MockAuth())

    # -----------------------------
    # CALL API
    # -----------------------------
    response = client.post(
        "/webauthn/login/finish",
        json={"id": "cred123"}
    )

    assert response.status_code == 200
    assert "access_token" in response.json()
