def test_webauthn_login_flow(client, override_dep, monkeypatch):

    import uuid
    import app.api.webauthn_router as router_module
    from app.dependencies.services import get_webauthn_service
    from app.dependencies.auth_dependencies import get_auth_service

    # -----------------------------
    # Fake user
    # -----------------------------
    user = type(
        "User",
        (),
        {
            "id": uuid.uuid4(),
            "email": "test@test.com",
            "is_active": True
        }
    )()

    # -----------------------------
    # Mock UserRepository (CRITICAL)
    # -----------------------------
    class FakeUserRepo:
        def __init__(self, db):
            pass

        def find_by_email(self, email):
            return user

    monkeypatch.setattr(router_module, "UserRepository", FakeUserRepo)

    # -----------------------------
    # SINGLE SERVICE INSTANCE (IMPORTANT)
    # -----------------------------
    class MockWebAuthnService:

        def __init__(self):
            self.challenge = "abc123"

        def start_login(self, user):
            return {"publicKey": {"challenge": self.challenge}}

        def finish_login(self, credential):
            # simulate successful validation
            return user

    webauthn_service = MockWebAuthnService()

    # -----------------------------
    # Mock AuthService
    # -----------------------------
    class MockAuthService:
        def create_session(self, *args, **kwargs):
            return {
                "access_token": "token",
                "refresh_token": "refresh",
                "token_type": "bearer"
            }

    # -----------------------------
    # Override dependencies
    # -----------------------------
    override_dep(get_webauthn_service, lambda: webauthn_service)
    override_dep(get_auth_service, lambda: MockAuthService())

    # -----------------------------
    # STEP 1: Start login
    # -----------------------------
    res1 = client.post(
        "/webauthn/login/start",
        json={"email": "test@test.com"}
    )

    assert res1.status_code == 200

    # -----------------------------
    # STEP 2: Finish login
    # -----------------------------
    res2 = client.post(
        "/webauthn/login/finish",
        json={"id": "cred123"}
    )

    assert res2.status_code == 200
    assert "access_token" in res2.json()