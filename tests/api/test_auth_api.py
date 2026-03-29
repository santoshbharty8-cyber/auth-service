import uuid

from app.models.user import User
from app.models.user_session import UserSession
from app.security.dependencies import get_current_user
from app.dependencies.auth_dependencies import get_recovery_code_service
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from app.rbac.dependencies import require_permission

def test_register_failure_400(client, mock_auth_service):
    mock_auth_service.register.side_effect = Exception("Registration error")

    response = client.post(
        "/auth/register",
        json={"email": "fail@example.com", "password": "password123"}
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Registration error"

def test_revoke_session_forbidden(client, db, create_admin_user, create_verified_user):
    admin = create_admin_user()

    user_data = create_verified_user()
    other_user = db.query(User).filter_by(email=user_data["email"]).first()

    session = UserSession(
        user_id=other_user.id,
        refresh_token_hash="other-refresh-hash",
        user_agent="test-agent",
        ip_address="127.0.0.1"
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    response = client.delete(
        f"/auth/sessions/{session.id}",
        headers=admin["headers"]
    )

    assert response.status_code == 403

def test_invalid_oauth_state_callbacks(client, monkeypatch):
    def mock_consume_state(redis, state):
        return None
    
    monkeypatch.setattr(
        "app.api.auth.OAuthHelper.consume_state",
        mock_consume_state
    )

    response_google = client.get("/auth/oauth/google/callback?code=abc&state=invalid")
    assert response_google.status_code == 400

    response_github = client.get("/auth/oauth/github/callback?code=abc&state=invalid")
    assert response_github.status_code == 400

def test_request_otp_rate_limited(client, monkeypatch):
    def mock_rate_limit(identifier):
        return False
    
    monkeypatch.setattr("app.api.auth.otp_service.rate_limit", mock_rate_limit)

    response = client.post(
        "/auth/request-otp",
        json={"email": "test@example.com"}
    )

    assert response.status_code == 429
    assert response.json()["detail"] == "Too many OTP requests. Please try later."


def test_request_otp_success(client, monkeypatch):
    def mock_rate_limit(identifier):
        return True

    monkeypatch.setattr("app.api.auth.otp_service.rate_limit", mock_rate_limit)
    monkeypatch.setattr("app.api.auth.otp_service.generate_otp", lambda identifier, fingerprint, ip: "123456")

    response = client.post(
        "/auth/request-otp",
        json={"email": "test@example.com"}
    )

    assert response.status_code == 200
    assert response.json()["message"] == "OTP sent successfully"

def test_login_otp_two_factor_and_direct(client, mock_auth_service, monkeypatch):
    # 2FA required path
    test_user = User(email="a@test.com")
    mock_auth_service.authenticate.return_value = test_user
    mock_auth_service.require_2fa.return_value = True
    
    class MockMFAChallenge:
        def create_challenge(self, uid):
            return "mfa-token"
    
    mock_auth_service.mfa_challenge = MockMFAChallenge()
    
    response = client.post(
        "/auth/login-otp",
        json={"email": "test@example.com", "otp": "123456"}
    )

    assert response.status_code == 200
    assert response.json()["require_2fa"] is True

    # No 2FA path
    mock_auth_service.require_2fa.return_value = False
    mock_auth_service.create_session.return_value = {"access_token": "a", "refresh_token": "r"}

    response = client.post(
        "/auth/login-otp",
        json={"email": "test@example.com", "otp": "123456"}
    )

    assert response.status_code == 200
    assert response.json()["access_token"] == "a"

def test_oauth_google_and_github_callback_flows(client, mock_auth_service, monkeypatch, override_dep):
    # direct invocation of endpoint functions (router might not be hit in some environments)
    user = User(id=uuid.uuid4(), email="u@test.com")

    mock_auth_service.start_google_oauth.return_value = "https://google.com/oauth"
    result = __import__('app.api.auth', fromlist=['start_link_google']).start_link_google(
        current_user=user,
        service=mock_auth_service,
    )
    
    assert 'redirect_url' in result


    mock_auth_service.start_github_oauth.return_value = "https://github.com/oauth"
    result = __import__('app.api.auth', fromlist=['github_login']).github_login(
        service=mock_auth_service,
    )
    assert hasattr(result, 'status_code')

    result = __import__('app.api.auth', fromlist=['github_link_start']).github_link_start(
        current_user=user,
        service=mock_auth_service,
    )
    assert 'redirect_url' in result

    # Google login flow
    def mock_consume_state_login(redis, state):
        return {"flow": "login", "code_verifier": "x"}
    
    monkeypatch.setattr("app.api.auth.OAuthHelper.consume_state", mock_consume_state_login)
    mock_auth_service.exchange_google_code.return_value = {"sub": "1"}
    mock_auth_service.handle_oauth_login.return_value = {"access_token": "g_access", "refresh_token": "g_refresh"}

    response = client.get("/auth/oauth/google/callback?code=abc&state=valid")
    assert response.status_code == 200
    assert response.json()["access_token"] == "g_access"

    # google invalid flow
    def mock_consume_state_invalid(redis, state):
        return {"flow": "invalid", "code_verifier": "x"}

    monkeypatch.setattr("app.api.auth.OAuthHelper.consume_state", mock_consume_state_invalid)
    response = client.get("/auth/oauth/google/callback?code=abc&state=valid")
    assert response.status_code == 400

    # Google link flow
    def mock_consume_state_link(redis, state):
        return {"flow": "link", "user_id": str(uuid.uuid4()), "code_verifier": "x"}
    
    monkeypatch.setattr("app.api.auth.OAuthHelper.consume_state", mock_consume_state_link)
    mock_auth_service.link_google_account.return_value = {"message": "linked"}

    response = client.get("/auth/oauth/google/callback?code=abc&state=valid")
    assert response.status_code == 200
    assert response.json()["message"] == "linked"

    # GitHub invalid oauth state already handled in existing test; do provider exception path
    def mock_consume_state_login2(redis, state):
        return {"flow": "login", "code_verifier": "x"}
    
    monkeypatch.setattr("app.api.auth.OAuthHelper.consume_state", mock_consume_state_login2)

    class FakeProvider:
        async def exchange_code(self, code, verifier):
            raise Exception("bad code")

    github_provider = FakeProvider()
    mock_auth_service.provider_registry.get_provider.return_value = github_provider

    response = client.get("/auth/oauth/github/callback?code=abc&state=valid")
    assert response.status_code == 400

    # GitHub login flow no 2FA
    class FakeProvider2:
        async def exchange_code(self, code, verifier):
            return "token"

        async def fetch_user(self, token):
            return {"id": "123"}

        async def fetch_email(self, token):
            return "user@example.com"

    github_provider2 = FakeProvider2()
    mock_auth_service.provider_registry.get_provider.return_value = github_provider2
    mock_auth_service.handle_github_oauth_login.return_value = User(email="g@test.com")
    mock_auth_service.require_2fa.return_value = False
    mock_auth_service.create_session.return_value = {"access_token": "gh_access", "refresh_token": "gh_refresh"}

    response = client.get("/auth/oauth/github/callback?code=abc&state=valid")
    assert response.status_code == 200
    assert response.json()["access_token"] == "gh_access"

    # GitHub login flow with 2FA required
    mock_auth_service.require_2fa.return_value = True
    
    class MockMFAChallenge2:
        def create_challenge(self, uid):
            return "gh-mfa"
    
    mock_auth_service.mfa_challenge = MockMFAChallenge2()

    response = client.get("/auth/oauth/github/callback?code=abc&state=valid")
    assert response.status_code == 200
    assert response.json()["require_2fa"] is True

    # GitHub link flow
    def mock_consume_state_link2(redis, state):
        return {"flow": "link", "user_id": str(uuid.uuid4()), "code_verifier": "x"}
    
    monkeypatch.setattr("app.api.auth.OAuthHelper.consume_state", mock_consume_state_link2)
    mock_auth_service.link_github_account.return_value = {"message": "github linked"}

    response = client.get("/auth/oauth/github/callback?code=abc&state=valid")
    assert response.status_code == 200
    assert response.json()["message"] == "github linked"

    # github invalid flow
    monkeypatch.setattr("app.api.auth.OAuthHelper.consume_state", lambda redis, state: {"flow": "invalid", "code_verifier": "x"})
    response = client.get("/auth/oauth/github/callback?code=abc&state=valid")
    assert response.status_code == 400


def test_2fa_recovery_codes(client, mock_auth_service, override_dep):
    user = User(id=uuid.uuid4(), email="u@test.com")
    override_dep(get_current_user, lambda: user)

    class FakeRecoveryService:
        def generate_codes(self, user_id):
            return ["r1", "r2"]

    override_dep(get_recovery_code_service, lambda: FakeRecoveryService())
    mock_auth_service.recovery_code_repo = Mock()

    response = client.post("/auth/2fa/recovery-codes")

    assert response.status_code == 200
    assert response.json()["recovery_codes"] == ["r1", "r2"]


def test_2fa_login_and_recovery_branches(client, mock_auth_service, monkeypatch, override_dep):
    user_id = uuid.uuid4()
    user = User(id=user_id, email="u@test.com")

    # 2FA login branch: not enabled
    mock_auth_service.mfa_challenge.check_attempts.return_value = True
    mock_auth_service.mfa_challenge.verify_challenge.return_value = user_id
    mock_auth_service.user_repo.find_by_id.return_value = user

    class FakeTOTPRepo:
        def find_by_user(self, uid):
            return SimpleNamespace(is_enabled=False, secret="s")

    class FakeTOTPService:
        def verify(self, secret, code):
            return False

    monkeypatch.setattr("app.api.auth.TOTPRepository", lambda db: FakeTOTPRepo())
    monkeypatch.setattr("app.api.auth.TOTPService", lambda: FakeTOTPService())

    response = client.post("/auth/2fa/login", json={"mfa_token": "m1", "code": "123456"})
    assert response.status_code == 400

    # 2FA login invalid code
    mock_auth_service.mfa_challenge.verify_challenge.return_value = user_id
    mock_auth_service.user_repo.find_by_id.return_value = user
    class FakeTOTPRepo2:
        def find_by_user(self, uid):
            return SimpleNamespace(is_enabled=True, secret="s")

    class FakeTOTPService2:
        def verify(self, secret, code):
            return False

    monkeypatch.setattr("app.api.auth.TOTPRepository", lambda db: FakeTOTPRepo2())
    monkeypatch.setattr("app.api.auth.TOTPService", lambda: FakeTOTPService2())

    response = client.post("/auth/2fa/login", json={"mfa_token": "m1", "code": "123456"})
    assert response.status_code == 401
    mock_auth_service.mfa_challenge.increment_attempt.assert_called_once()

    # 2FA login success
    mock_auth_service.mfa_challenge.verify_challenge.return_value = user_id
    mock_auth_service.user_repo.find_by_id.return_value = user
    mock_auth_service.create_session.return_value = {"access_token": "x", "refresh_token": "y"}

    class FakeTOTPRepo3:
        def find_by_user(self, uid):
            return SimpleNamespace(is_enabled=True, secret="s")

    class FakeTOTPService3:
        def verify(self, secret, code):
            return True

    monkeypatch.setattr("app.api.auth.TOTPRepository", lambda db: FakeTOTPRepo3())
    monkeypatch.setattr("app.api.auth.TOTPService", lambda: FakeTOTPService3())

    response = client.post("/auth/2fa/login", json={"mfa_token": "m1", "code": "123456"})
    assert response.status_code == 200
    assert response.json()["access_token"] == "x"
    mock_auth_service.mfa_challenge.delete_challenge.assert_called()

    # 2FA recovery: too many attempts
    mock_auth_service.mfa_challenge.check_attempts.return_value = False
    response = client.post("/auth/2fa/recovery", json={"mfa_token": "m2", "recovery_code": "rc"})
    assert response.status_code == 429

    # 2FA recovery: invalid challenge
    mock_auth_service.mfa_challenge.check_attempts.return_value = True
    mock_auth_service.mfa_challenge.verify_challenge.return_value = None

    response = client.post("/auth/2fa/recovery", json={"mfa_token": "m2", "recovery_code": "rc"})
    assert response.status_code == 401

    # 2FA recovery: user not found
    mock_auth_service.mfa_challenge.verify_challenge.return_value = user_id
    mock_auth_service.user_repo.find_by_id.return_value = None

    response = client.post("/auth/2fa/recovery", json={"mfa_token": "m2", "recovery_code": "rc"})
    assert response.status_code == 404

    # 2FA recovery: invalid recovery code
    mock_auth_service.user_repo.find_by_id.return_value = user

    class FakeRecoveryService:
        def verify_code(self, uid, code):
            return False

    override_dep(get_recovery_code_service, lambda: FakeRecoveryService())

    response = client.post("/auth/2fa/recovery", json={"mfa_token": "m2", "recovery_code": "rc"})
    assert response.status_code == 401
    mock_auth_service.mfa_challenge.increment_attempt.assert_called()

    # 2FA recovery success
    class FakeRecoveryService2:
        def verify_code(self, uid, code):
            return True

    override_dep(get_recovery_code_service, lambda: FakeRecoveryService2())
    mock_auth_service.create_session.return_value = {"access_token": "a", "refresh_token": "b"}

    response = client.post("/auth/2fa/recovery", json={"mfa_token": "m2", "recovery_code": "rc"})
    assert response.status_code == 200
    assert response.json()["access_token"] == "a"


    mock_auth_service.login.return_value = {
        "access_token": "access",
        "refresh_token": "refresh",
    }

    response = client.post(
        "/auth/login",
        json={"email": "test@example.com", "password": "pass"}
    )

    assert response.status_code == 200
    assert response.json()["access_token"] == "access"

def test_refresh_success(client, mock_auth_service):

    mock_auth_service.refresh.return_value = {
        "access_token": "new_access",
        "refresh_token": "new_refresh",
    }

    response = client.post(
        "/auth/refresh",
        json={"refresh_token": "refresh"}
    )

    assert response.status_code == 200
    assert response.json()["access_token"] == "new_access"

def test_logout_success(client, mock_auth_service):

    mock_auth_service.logout.return_value = {"message": "Logged out"}

    response = client.post(
        "/auth/logout",
        headers={"Authorization": "Bearer access"},
        json={"refresh_token": "refresh"}
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Logged out"

def test_me_success(client, create_admin_user):

    admin = create_admin_user()

    response = client.get(
        "/auth/me",
        headers=admin["headers"]
    )

    assert response.status_code == 200
    assert response.json()["email"] == admin["email"]

def test_me_without_token(client):

    response = client.get("/auth/me")

    assert response.status_code in (401, 403)

def test_force_logout_all(client, create_admin_user):

    admin = create_admin_user()

    response = client.post(
        "/auth/force-logout-all",
        headers=admin["headers"]
    )

    assert response.status_code == 200

def test_audit_logs(client, create_admin_user):

    admin = create_admin_user()

    response = client.get(
        "/auth/audit-logs",
        headers=admin["headers"]
    )

    assert response.status_code == 200

def test_password_reset_request(client, mock_auth_service):

    mock_auth_service.request_password_reset.return_value = {
        "message": "reset sent"
    }

    response = client.post(
        "/auth/password-reset/request",
        json={"email": "test@example.com"}
    )

    assert response.status_code == 200

def test_password_reset_confirm(client, mock_auth_service):

    mock_auth_service.reset_password.return_value = {
        "message": "password reset"
    }

    response = client.post(
        "/auth/password-reset/confirm",
        json={"token": "t", "new_password": "abc"}
    )

    assert response.status_code == 200

def test_verify_email(client, mock_auth_service):

    mock_auth_service.verify_email.return_value = {
        "message": "verified"
    }

    response = client.post(
        "/auth/verify-email",
        json={"token": "t"}
    )

    assert response.status_code == 200

def test_resend_verification(client, mock_auth_service):

    mock_auth_service.resend_verification.return_value = {
        "verification_token": "vt"
    }

    response = client.post(
        "/auth/resend-verification",
        json={"email": "test@example.com"}
    )

    assert response.status_code == 200

    # safer assertion (API may not expose token)
    assert "message" in response.json()

