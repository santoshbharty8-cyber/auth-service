import json
import uuid
from datetime import datetime, timedelta, UTC
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.services import auth_service
from app.services.auth_service import AuthService
from app.models import User, OAuthAccount


# ----------------------------------------
# FAKE REPOSITORIES
# ----------------------------------------

class FakeUserRepo:

    def __init__(self):
        self.users = {}

    def exists_by_email(self, email):
        return email in self.users

    def create(self, user):
        if getattr(user, "id", None) is None:
            user.id = uuid.uuid4()
        self.users[user.email] = user
        return user

    def find_by_email(self, email):
        return self.users.get(email)

    def find_by_id(self, user_id):
        for user in self.users.values():
            if str(user.id) == str(user_id):
                return user
        return None

    def save(self, user):
        if user.email:
            self.users[user.email] = user
        return user


class FakeSessionRepo:

    def __init__(self):
        self.sessions = {}
        self.tokens = {}
        self.revoked = []
        self.revoked_all = []

    def create(self, session):
        self.sessions[session.refresh_token_hash] = session
        return session

    def find_by_hash(self, token_hash):
        return self.sessions.get(token_hash)

    def revoke(self, session):
        self.revoked.append(session)

    def revoke_all_for_user(self, user_id):
        self.revoked_all.append(user_id)

    def find_active_by_user(self, user_id):
        return []
    
    def save(self, session):   # ✅ ADD THIS
        self.sessions[session.refresh_token_hash] = session
        return session


class FakeAuditService:

    def enqueue_event(self, *args, **kwargs):
        pass


class FakePasswordResetRepo:

    def __init__(self):
        self.tokens = {}

    def create(self, token):
        self.tokens[token.token_hash] = token
        return token

    def find_by_hash(self, token_hash):
        return self.tokens.get(token_hash)

    def delete(self, token):
        self.tokens.pop(token.token_hash, None)


class FakeEmailVerificationRepo:

    def __init__(self):
        self.tokens = {}

    def create(self, token):
        self.tokens[token.token_hash] = token
        return token

    def find_by_hash(self, token_hash):
        return self.tokens.get(token_hash)

    def delete(self, token):
        self.tokens.pop(token.token_hash, None)

    def delete_by_user_id(self, user_id):
        to_delete = [
            k for k, v in self.tokens.items()
            if v.user_id == user_id
        ]
        for k in to_delete:
            del self.tokens[k]


class FakeProviderRegistry:

    def __init__(self, providers=None):
        self.providers = providers or {}

    def get_provider(self, method):
        return self.providers.get(method)


class FakeDeviceRepo:

    def find_device(self, user_id, fingerprint):
        return None

    def create_device(self, *args, **kwargs):
        pass


class FakeTOTPRepo:

    def find_by_user(self, user_id):
        return None


class FakeRecoveryCodeRepo:

    def find_by_user(self, user_id):
        return []


class FakeMFAChallenge:

    def check_attempts(self, token):
        return True

    def verify_challenge(self, token):
        return uuid.uuid4()   # ✅ MUST RETURN UUID

    def increment_attempt(self, token):
        return True

    def delete_challenge(self, token):
        return True

    def create_challenge(self, user_id):
        return "mfa-token"


class FakeOAuthRepo:

    def find_by_provider_user_id(self, *args, **kwargs):
        return None

    def create(self, *args, **kwargs):
        pass


# ----------------------------------------
# TEST
# ----------------------------------------

def test_register_service_success():

    user_repo = FakeUserRepo()
    session_repo = FakeSessionRepo()
    audit_service = FakeAuditService()
    password_reset_repo = FakePasswordResetRepo()
    email_verification_repo = FakeEmailVerificationRepo()
    provider_registry = FakeProviderRegistry()
    mfa_challenge = FakeMFAChallenge()
    oauth_repo = FakeOAuthRepo()
    device_repo = FakeDeviceRepo()
    totp_repo = FakeTOTPRepo()
    recovery_code_repo = FakeRecoveryCodeRepo()

    service = AuthService(
        user_repo=user_repo,
        session_repo=session_repo,
        audit_service=audit_service,
        password_reset_repo=password_reset_repo,
        email_verification_repo=email_verification_repo,
        provider_registry=provider_registry,
        mfa_challenge=mfa_challenge,
        oauth_repo=oauth_repo,
        device_repo=device_repo,
        totp_repo=totp_repo,
        recovery_code_repo=recovery_code_repo,
    )

    # ----------------------------------------
    # MOCK INTERNAL METHODS
    # ----------------------------------------

    service.hash_password = lambda pwd: "hashed_password"

    # ✅ IMPORTANT: mock token creation
    service.create_email_verification_token = lambda user_id: type(
        "Token",
        (),
        {
            "token_hash": "hash123",
            "raw_token": "raw_token_123",
            "user_id": user_id
        }
    )()

    # ----------------------------------------
    # EXECUTE
    # ----------------------------------------

    result = service.register("service@example.com", "StrongPass123")

    user = result["user"]

    # ----------------------------------------
    # ASSERTIONS
    # ----------------------------------------

    assert user.email == "service@example.com"
    assert user.id is not None   # ✅ UUID assigned
    assert result["verification_token"] is not None


# Helper fixtures and providers
class DummyRedis:
    def __init__(self):
        self.store = {}

    def set(self, key, value, nx=False, ex=None):
        if nx and key in self.store:
            return False
        self.store[key] = value
        return True

    def setex(self, key, exp, value):
        self.store[key] = value

    def get(self, key):
        return self.store.get(key)

    def delete(self, key):
        self.store.pop(key, None)


class SimpleProvider:
    def __init__(self, user=None, authentic=True):
        self.user = user
        self.authentic = authentic

    def authenticate(self, request_data):
        return self.user if self.authentic else None


def make_service(monkeypatch, **overrides):
    user_repo = overrides.get("user_repo", FakeUserRepo())
    session_repo = overrides.get("session_repo", FakeSessionRepo())
    audit_service = overrides.get("audit_service", FakeAuditService())
    password_reset_repo = overrides.get("password_reset_repo", FakePasswordResetRepo())
    email_verification_repo = overrides.get("email_verification_repo", FakeEmailVerificationRepo())
    provider_registry = overrides.get("provider_registry", FakeProviderRegistry())
    mfa_challenge = overrides.get("mfa_challenge", FakeMFAChallenge())
    oauth_repo = overrides.get("oauth_repo", FakeOAuthRepo())
    device_repo = overrides.get("device_repo", FakeDeviceRepo())
    totp_repo = overrides.get("totp_repo", FakeTOTPRepo())
    recovery_code_repo = overrides.get("recovery_code_repo", FakeRecoveryCodeRepo())

    service = AuthService(
        user_repo=user_repo,
        session_repo=session_repo,
        audit_service=audit_service,
        password_reset_repo=password_reset_repo,
        email_verification_repo=email_verification_repo,
        provider_registry=provider_registry,
        mfa_challenge=mfa_challenge,
        oauth_repo=oauth_repo,
        device_repo=device_repo,
        totp_repo=totp_repo,
        recovery_code_repo=recovery_code_repo,
    )

    monkeypatch.setattr(auth_service, "hash_password", lambda pwd: f"hash-{pwd}")
    monkeypatch.setattr(auth_service, "hash_token", lambda t: f"hash-{t}")
    monkeypatch.setattr(auth_service, "verify_password", lambda raw, hashed: hashed == f"hash-{raw}")
    monkeypatch.setattr(auth_service, "generate_refresh_token", lambda: "refresh-token")
    # monkeypatch.setattr(auth_service, "generate_secure_token", lambda: "refresh-token")
    monkeypatch.setattr(auth_service, "create_access_token", lambda data, token_version: "access-token")
    monkeypatch.setattr(auth_service, "decode_access_token", lambda token: {"jti": "jti-123", "exp": int(datetime.now(UTC).timestamp()) + 3600})
    monkeypatch.setattr(auth_service, "blacklist_token", lambda jti, ttl: None)
    monkeypatch.setattr(auth_service, "generate_device_fingerprint", lambda ua, ip: "fingerprint")
    monkeypatch.setattr(auth_service, "create_magic_link_token", lambda user_id, email, fingerprint, ip: "magic-token")
    monkeypatch.setattr(auth_service, "verify_magic_link_token", lambda token: {
        "jti": "magic-jti",
        "sub": "user-1",
        "fingerprint": "fingerprint",
        "ip": "127.0.0.1"
    })
    monkeypatch.setattr(auth_service, "redis_client", DummyRedis())

    return service, user_repo, session_repo, audit_service, mfa_challenge, email_verification_repo, password_reset_repo, oauth_repo, device_repo, totp_repo, recovery_code_repo


def make_user(email="user@example.com", **kwargs):
    base = {
        "id": uuid.uuid4(),
        "email": email,
        "password_hash": "hash-Secret",
        "status": "ACTIVE",
        "failed_attempts": 0,
        "locked_until": None,
        "token_version": 0,
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_authenticate_unsupported_method(monkeypatch):
    service, *_ = make_service(monkeypatch)
    with pytest.raises(HTTPException) as exc:
        service.authenticate("unknown", {})
    assert exc.value.status_code == 400


def test_login_invalid_credentials(monkeypatch):
    service, user_repo, *_ = make_service(monkeypatch)
    user_repo.create(make_user("john@example.com"))
    # provider returns None => invalid login
    service.provider_registry = FakeProviderRegistry({"password": SimpleProvider(None, authentic=False)})

    with pytest.raises(HTTPException) as exc:
        service.login("john@example.com", "bad", "ua", "127.0.0.1")
    assert exc.value.status_code == 401
    assert user_repo.find_by_email("john@example.com").failed_attempts == 1


def test_login_requires_2fa(monkeypatch):
    totp_repo = FakeTOTPRepo()
    totp_repo.find_by_user = lambda user_id: SimpleNamespace(is_enabled=True)
    service, user_repo, *_ = make_service(monkeypatch, totp_repo=totp_repo)
    user_repo.create(make_user("john2@example.com"))
    service.provider_registry = FakeProviderRegistry({"password": SimpleProvider(make_user("john2@example.com"), authentic=True)})

    result = service.login("john2@example.com", "Secret", "ua", "127.0.0.1")
    assert result["require_2fa"] is True


def test_login_success_creates_session(monkeypatch):
    session_repo = FakeSessionRepo()
    service, user_repo, session_repo, *_ = make_service(monkeypatch, session_repo=session_repo)
    u = make_user("john3@example.com")
    user_repo.create(u)
    service.provider_registry = FakeProviderRegistry({"password": SimpleProvider(u, authentic=True)})

    result = service.login("john3@example.com", "Secret", "ua", "127.0.0.1")
    assert result["access_token"] == "access-token"
    assert result["refresh_token"] == "refresh-token"


def test_refresh_invalid_token(monkeypatch):
    service, *_ = make_service(monkeypatch)
    with pytest.raises(HTTPException) as exc:
        service.refresh("missing")
    assert exc.value.status_code == 403


def test_refresh_success(monkeypatch):
    service, user_repo, session_repo, *_ = make_service(monkeypatch)
    u = make_user("refresh@example.com")
    user_repo.create(u)
    sess = SimpleNamespace(user_id=u.id, refresh_token_hash="hash-refresh", last_active_at=datetime.now(UTC))
    session_repo.sessions["hash-refresh"] = sess

    result = service.refresh("refresh")
    assert result["access_token"] == "access-token"
    assert result["refresh_token"] == "refresh-token"


def test_logout_invalid_session(monkeypatch):
    service, *_ = make_service(monkeypatch)
    with pytest.raises(HTTPException) as exc:
        service.logout("bad", "token")
    assert exc.value.status_code == 400


def test_logout_blacklist_and_success(monkeypatch):
    service, user_repo, session_repo, *_ = make_service(monkeypatch)
    u = make_user("logout@example.com")
    user_repo.create(u)
    session_repo.sessions["hash-refresh"] = SimpleNamespace(user_id=u.id, refresh_token_hash="hash-refresh")

    # set access token payload to non-expired
    monkeypatch.setattr(auth_service, "decode_access_token", lambda t: {"jti": "jti-123", "exp": int(datetime.now(UTC).timestamp()) + 3600})

    result = service.logout("refresh", "token")
    assert result["message"] == "Logged out successfully"
    assert session_repo.revoked


def test_force_logout_all_user_not_found(monkeypatch):
    service, *_ = make_service(monkeypatch)
    with pytest.raises(HTTPException) as exc:
        service.force_logout_all("missing")
    assert exc.value.status_code == 404


def test_force_logout_all_success(monkeypatch):
    service, user_repo, session_repo, *_ = make_service(monkeypatch)
    u = make_user("force@example.com")
    user_repo.create(u)
    result = service.force_logout_all(u.id)
    assert result["message"] == "All sessions invalidated"
    assert session_repo.revoked_all == [u.id]


def test_password_reset_pathways(monkeypatch):
    result = make_service(monkeypatch)
    service, user_repo, session_repo, audit_service, mfa_challenge, email_verification_repo, password_reset_repo = result[0], result[1], result[2], result[3], result[4], result[5], result[6]
    assert service.request_password_reset("absent@example.com")["message"].startswith("If the email exists")

    u = make_user("reset@example.com")
    user_repo.create(u)
    response = service.request_password_reset("reset@example.com")
    assert "reset_token" in response and isinstance(response["reset_token"], str)

    # invalid token
    with pytest.raises(HTTPException):
        service.reset_password("bad-token", "new")

    # expired token
    token_hash = "hash-expired"
    password_reset_repo.tokens[token_hash] = SimpleNamespace(user_id=u.id, expires_at=datetime.now(UTC) - timedelta(minutes=1), token_hash=token_hash)
    with pytest.raises(HTTPException):
        service.reset_password("expired", "new")

    # success path
    good_hash = "hash-token"
    password_reset_repo.tokens[good_hash] = SimpleNamespace(user_id=u.id, expires_at=datetime.now(UTC) + timedelta(minutes=10), token_hash=good_hash)
    # monkeypatch hash_token to return good_hash
    monkeypatch.setattr(auth_service, "hash_token", lambda t: good_hash)
    result = service.reset_password("token", "newpass")
    assert result["message"] == "Password updated successfully"


def test_verify_email_resend(monkeypatch):
    result = make_service(monkeypatch)
    service, user_repo, session_repo, audit_service, mfa_challenge, email_verification_repo = result[0], result[1], result[2], result[3], result[4], result[5]
    with pytest.raises(HTTPException):
        service.verify_email("bad")

    u = make_user("verify@example.com", status="PENDING")
    user_repo.create(u)
    token_hash = "hash-verify"
    email_verification_repo.tokens[token_hash] = SimpleNamespace(user_id=u.id, expires_at=datetime.now(UTC) + timedelta(minutes=10), token_hash=token_hash)
    monkeypatch.setattr(auth_service, "hash_token", lambda t: token_hash)

    result = service.verify_email("tok")
    assert result["message"] == "Email verified successfully"
    assert user_repo.find_by_email("verify@example.com").status == "ACTIVE"

    with pytest.raises(HTTPException):
        service.resend_verification("missing@example.com")

    u_active = make_user("active@example.com", status="ACTIVE")
    user_repo.create(u_active)
    with pytest.raises(HTTPException):
        service.resend_verification("active@example.com")

    u_pending = make_user("pending@example.com", status="PENDING")
    user_repo.create(u_pending)
    result = service.resend_verification("pending@example.com")
    assert "verification_token" in result


def test_require_2fa(monkeypatch):
    totp_repo = FakeTOTPRepo()
    totp_repo.find_by_user = lambda uid: SimpleNamespace(is_enabled=True)
    service, *_ = make_service(monkeypatch, totp_repo=totp_repo)
    assert service.require_2fa(make_user()) is True


def test_oauth_flows(monkeypatch):
    result = make_service(monkeypatch)
    service, user_repo, session_repo, audit_service, mfa_challenge, email_verification_repo, password_reset_repo, oauth_repo = result[0], result[1], result[2], result[3], result[4], result[5], result[6], result[7]
    provider_payload = {"sub": "o1", "email": "o@example.com"}

    # exchange_google_code
    fake_provider = SimpleNamespace(exchange_code_for_token=lambda c, v: {"id_token": "id"}, verify_identity=lambda token: provider_payload)
    service.provider_registry = FakeProviderRegistry({"google_oauth": fake_provider})
    assert service.exchange_google_code("c", "v") == provider_payload

    # handle_oauth_login link_required
    oauth_repo.find_by_provider_user_id = lambda provider, pid: None
    result = service.handle_oauth_login(provider_payload, "ua", "127.0.0.1")
    assert result["status"] == "link_required"

    # handle_oauth_login with oauth account and no 2fa
    u = make_user("oauthuser@example.com")
    user_repo.create(u)
    oauth_repo.find_by_provider_user_id = lambda provider, pid: SimpleNamespace(user=u)
    result = service.handle_oauth_login(provider_payload, "ua", "127.0.0.1")
    assert "access_token" in result

    # link_google_account existing
    oauth_repo.find_by_provider_user_id = lambda provider, pid: SimpleNamespace()
    with pytest.raises(HTTPException):
        service.link_google_account(u.id, provider_payload)

    # link_google_account success
    oauth_repo.find_by_provider_user_id = lambda provider, pid: None
    out = service.link_google_account(u.id, provider_payload)
    assert out["message"] == "Google account linked successfully"

    # handle_github_oauth_login existing oauth
    oauth_repo.find_by_provider_user_id = lambda provider, pid: SimpleNamespace(user=u)
    assert service.handle_github_oauth_login("github", {"provider_user_id": "x", "email": "x@example.com"}) == u

    # existing email user conflict
    oauth_repo.find_by_provider_user_id = lambda provider, pid: None
    with pytest.raises(HTTPException):
        service.handle_github_oauth_login("github", {"provider_user_id": "x2", "email": "oauthuser@example.com"})

    # new user creation
    got = service.handle_github_oauth_login("github", {"provider_user_id": "x2", "email": "new@example.com"})
    assert got.email == "new@example.com"

    # link_github_account existing
    oauth_repo.find_by_provider_user_id = lambda provider, pid: SimpleNamespace()
    with pytest.raises(HTTPException):
        service.link_github_account(u.id, {"provider_user_id": "x", "email": "x@example.com"})

    # link_github_account success
    oauth_repo.find_by_provider_user_id = lambda provider, pid: None
    out2 = service.link_github_account(u.id, {"provider_user_id": "x", "email": "x@example.com"})
    assert out2["message"] == "GitHub account linked successfully"

    # handle_microsoft_oauth_login existing oauth
    oauth_repo.find_by_provider_user_id = lambda provider, pid: SimpleNamespace(user=u)
    assert service.handle_microsoft_oauth_login({"provider_user_id": "y", "email": "y@example.com"}) == u

    # existing email conflict
    oauth_repo.find_by_provider_user_id = lambda provider, pid: None
    with pytest.raises(HTTPException):
        service.handle_microsoft_oauth_login({"provider_user_id": "y2", "email": "oauthuser@example.com"})

    # fresh user created
    nm = service.handle_microsoft_oauth_login({"provider_user_id": "y2", "email": "fresh@example.com"})
    assert nm.email == "fresh@example.com"

    # link_microsoft_account existing
    oauth_repo.find_by_provider_user_id = lambda provider, pid: SimpleNamespace()
    with pytest.raises(HTTPException):
        service.link_microsoft_account(u.id, {"provider_user_id": "y", "email": "x@example.com"})

    oauth_repo.find_by_provider_user_id = lambda provider, pid: None
    out3 = service.link_microsoft_account(u.id, {"provider_user_id": "y", "email": "x3@example.com"})
    assert out3["message"] == "Microsoft account linked successfully"


def test_magic_link_flows(monkeypatch):
    service, user_repo, device_repo, *_ = make_service(monkeypatch)
    user_repo.create(make_user("magic@example.com", id="user-1"))

    # request_magic_link missing user
    assert service.request_magic_link("no@example.com", "ua", "127.0.0.1")["message"].startswith("If email exists")

    # request_magic_link existing
    assert service.request_magic_link("magic@example.com", "ua", "127.0.0.1")["message"] == "Magic login link sent"

    # login_with_magic_link first attempt -> suspicious path (no known device)
    result = service.login_with_magic_link("magic-token", "ua", "127.0.0.1")
    assert result["approval_required"] is True

    # approve login missing approval
    with pytest.raises(HTTPException):
        service.approve_login("missing", "ua", "127.0.0.1")

    # add approval request and approve
    redis_client = auth_service.redis_client
    redis_client.setex("login_approval:rid", 300, json.dumps({"user_id": "user-1", "fingerprint": "fingerprint", "ip": "127.0.0.1"}))
    res = service.approve_login("rid", "ua", "127.0.0.1")
    assert res["access_token"] == "access-token"

def test_approve_login_missing_request(monkeypatch):
    service, *_ = make_service(monkeypatch)
    monkeypatch.setattr(auth_service, "redis_client", DummyRedis())

    with pytest.raises(HTTPException) as exc:
        service.approve_login("unknown-id", "ua", "127.0.0.1")
    assert exc.value.status_code == 400


def test_approve_login_success(monkeypatch):
    service, user_repo, device_repo, *_ = make_service(monkeypatch)
    u = make_user("approve@example.com", id="user-2")
    user_repo.create(u)
    redis = DummyRedis()
    data_payload = {"user_id": "user-2", "fingerprint": "fp", "ip": "127.0.0.1"}
    redis.setex("login_approval:rid", 300, json.dumps(data_payload))
    monkeypatch.setattr(auth_service, "redis_client", redis)

    res = service.approve_login("rid", "ua", "127.0.0.1")
    assert "access_token" in res or res["require_2fa"] is not True

def test_authenticate_unsupported(real_auth_service):
    with pytest.raises(HTTPException):
        real_auth_service.authenticate("invalid_method", {})

def test_refresh_invalid_session(real_auth_service, monkeypatch):
    monkeypatch.setattr(
        real_auth_service.session_repo,
        "find_by_hash",
        lambda x: None
    )

    with pytest.raises(HTTPException):
        real_auth_service.refresh("bad_token")

def test_reset_password_invalid(real_auth_service, monkeypatch):
    monkeypatch.setattr(
        real_auth_service.password_reset_repo,
        "find_by_hash",
        lambda x: None
    )

    with pytest.raises(HTTPException):
        real_auth_service.reset_password("bad", "newpass")

def test_reset_password_expired(real_auth_service, monkeypatch):
    token = SimpleNamespace(
        user_id="u1",
        expires_at=datetime.now(UTC) - timedelta(minutes=1)
    )

    monkeypatch.setattr(
        real_auth_service.password_reset_repo,
        "find_by_hash",
        lambda x: token
    )

    with pytest.raises(HTTPException):
        real_auth_service.reset_password("t", "new")

def test_verify_email_invalid(real_auth_service, monkeypatch):
    monkeypatch.setattr(
        real_auth_service.email_verification_repo,
        "find_by_hash",
        lambda x: None
    )

    with pytest.raises(HTTPException):
        real_auth_service.verify_email("bad")

def test_verify_email_expired(real_auth_service, monkeypatch):
    token = SimpleNamespace(
        user_id="u1",
        expires_at=datetime.now(UTC) - timedelta(hours=1)
    )

    monkeypatch.setattr(
        real_auth_service.email_verification_repo,
        "find_by_hash",
        lambda x: token
    )

    with pytest.raises(HTTPException):
        real_auth_service.verify_email("t")

def test_resend_verification_user_not_found(real_auth_service, monkeypatch):
    monkeypatch.setattr(
        real_auth_service.user_repo,
        "find_by_email",
        lambda x: None
    )

    with pytest.raises(HTTPException):
        real_auth_service.resend_verification("x@test.com")

def test_resend_verification_active(real_auth_service, monkeypatch):
    user = SimpleNamespace(id="u1", status="ACTIVE")

    monkeypatch.setattr(
        real_auth_service.user_repo,
        "find_by_email",
        lambda x: user
    )

    with pytest.raises(HTTPException):
        real_auth_service.resend_verification("x@test.com")

def test_magic_link_replay(real_auth_service, monkeypatch):

    monkeypatch.setattr(
        "app.services.auth_service.verify_magic_link_token",
        lambda x: {"jti": "j1", "sub": "u1", "fingerprint": "f", "ip": "1.1.1.1"}
    )

    # simulate already used
    monkeypatch.setattr(
        "app.services.auth_service.redis_client.set",
        lambda *a, **k: False
    )

    with pytest.raises(HTTPException):
        real_auth_service.login_with_magic_link("t", "ua", "1.1.1.1")

def test_magic_link_suspicious(real_auth_service, monkeypatch):

    monkeypatch.setattr(
        "app.services.auth_service.verify_magic_link_token",
        lambda x: {"jti": "j1", "sub": "u1", "fingerprint": "x", "ip": "2.2.2.2"}
    )

    monkeypatch.setattr(
        "app.services.auth_service.redis_client.set",
        lambda *a, **k: True
    )

    monkeypatch.setattr(
        real_auth_service.device_repo,
        "find_device",
        lambda *a: None
    )

    result = real_auth_service.login_with_magic_link("t", "ua", "1.1.1.1")

    assert result["approval_required"] is True

def test_approve_login_invalid(real_auth_service, monkeypatch):

    monkeypatch.setattr(
        "app.services.auth_service.redis_client.get",
        lambda x: None
    )

    with pytest.raises(HTTPException):
        real_auth_service.approve_login("bad", "ua", "ip")


def test_login_user_not_found(real_auth_service, monkeypatch):

    # user not found
    monkeypatch.setattr(
        real_auth_service.user_repo,
        "find_by_email",
        lambda email: None
    )

    calls = {}

    # track audit call
    monkeypatch.setattr(
        real_auth_service.audit_service,
        "enqueue_event",
        lambda **kwargs: calls.update(kwargs)
    )

    with pytest.raises(HTTPException) as exc:
        real_auth_service.login(
            email="notfound@test.com",
            password="pass",
            user_agent="ua",
            ip_address="127.0.0.1"
        )

    # ✅ assert exception
    assert exc.value.status_code == 401

    # ✅ assert audit logged correctly
    assert calls["event_type"] == "LOGIN"
    assert calls["event_status"] == "FAILURE"
    assert calls["metadata"]["reason"] == "user_not_found"

def test_logout_invalid_access_token_missing_fields(real_auth_service, monkeypatch):

    # valid session must exist (otherwise earlier branch fails)
    session = SimpleNamespace(user_id="u1")

    monkeypatch.setattr(
        real_auth_service.session_repo,
        "find_by_hash",
        lambda x: session
    )

    monkeypatch.setattr(
        real_auth_service.session_repo,
        "revoke",
        lambda x: None
    )

    # ❌ payload missing jti & exp
    monkeypatch.setattr(
        "app.services.auth_service.decode_access_token",
        lambda token: {}
    )

    with pytest.raises(HTTPException) as exc:
        real_auth_service.logout("valid_refresh", "bad_access")

    assert exc.value.status_code == 401
    assert "Invalid access token" in str(exc.value.detail)

def test_logout_missing_jti(real_auth_service, monkeypatch):

    session = SimpleNamespace(user_id="u1")

    monkeypatch.setattr(
        real_auth_service.session_repo,
        "find_by_hash",
        lambda x: session
    )

    monkeypatch.setattr(
        real_auth_service.session_repo,
        "revoke",
        lambda x: None
    )

    monkeypatch.setattr(
        "app.services.auth_service.decode_access_token",
        lambda token: {"exp": 999999}
    )

    with pytest.raises(HTTPException):
        real_auth_service.logout("r", "a")

def test_logout_missing_exp(real_auth_service, monkeypatch):

    session = SimpleNamespace(user_id="u1")

    monkeypatch.setattr(
        real_auth_service.session_repo,
        "find_by_hash",
        lambda x: session
    )

    monkeypatch.setattr(
        real_auth_service.session_repo,
        "revoke",
        lambda x: None
    )

    monkeypatch.setattr(
        "app.services.auth_service.decode_access_token",
        lambda token: {"jti": "abc"}
    )

    with pytest.raises(HTTPException):
        real_auth_service.logout("r", "a")


from jose import ExpiredSignatureError

def test_logout_expired_access_token(real_auth_service, monkeypatch):

    # valid session (so we reach this branch)
    session = SimpleNamespace(user_id="u1")

    monkeypatch.setattr(
        real_auth_service.session_repo,
        "find_by_hash",
        lambda x: session
    )

    monkeypatch.setattr(
        real_auth_service.session_repo,
        "revoke",
        lambda x: None
    )

    # 🔥 simulate expired token
    monkeypatch.setattr(
        "app.services.auth_service.decode_access_token",
        lambda token: (_ for _ in ()).throw(ExpiredSignatureError())
    )

    calls = {}

    monkeypatch.setattr(
        real_auth_service.audit_service,
        "enqueue_event",
        lambda **kwargs: calls.update(kwargs)
    )

    result = real_auth_service.logout("valid_refresh", "expired_access")

    # ✅ should NOT raise error
    assert result["message"] == "Logged out successfully"

    # ✅ audit should still be called
    assert calls["event_type"] == "LOGOUT"
    assert calls["event_status"] == "SUCCESS"

from jose import JWTError

def test_logout_invalid_access_token_jwt_error(real_auth_service, monkeypatch):

    # valid session required
    session = SimpleNamespace(user_id="u1")

    monkeypatch.setattr(
        real_auth_service.session_repo,
        "find_by_hash",
        lambda x: session
    )

    monkeypatch.setattr(
        real_auth_service.session_repo,
        "revoke",
        lambda x: None
    )

    # 🔥 simulate JWTError
    def raise_jwt_error(token):
        raise JWTError("invalid")

    monkeypatch.setattr(
        "app.services.auth_service.decode_access_token",
        raise_jwt_error
    )

    with pytest.raises(HTTPException) as exc:
        real_auth_service.logout("valid_refresh", "bad_access")

    assert exc.value.status_code == 401
    assert "Invalid access token" in str(exc.value.detail)

def test_force_logout_all_success(real_auth_service, monkeypatch):

    user = SimpleNamespace(id="u1", token_version=1)

    calls = {}

    monkeypatch.setattr(
        real_auth_service.user_repo,
        "find_by_id",
        lambda x: user
    )

    monkeypatch.setattr(
        real_auth_service.user_repo,
        "save",
        lambda u: calls.update({"saved": True})
    )

    monkeypatch.setattr(
        real_auth_service.session_repo,
        "revoke_all_for_user",
        lambda uid: calls.update({"revoked": uid})
    )

    monkeypatch.setattr(
        real_auth_service.audit_service,
        "enqueue_event",
        lambda **kwargs: calls.update({"audit": kwargs})
    )

    result = real_auth_service.force_logout_all("u1")

    assert user.token_version == 2
    assert calls["saved"] is True
    assert calls["revoked"] == "u1"
    assert calls["audit"]["event_type"] == "FORCE_LOGOUT_ALL"
    assert result["message"] == "All sessions invalidated"

def test_force_logout_all_user_not_found(real_auth_service, monkeypatch):

    monkeypatch.setattr(
        real_auth_service.user_repo,
        "find_by_id",
        lambda x: None
    )

    with pytest.raises(HTTPException):
        real_auth_service.force_logout_all("bad_user")

def test_request_password_reset_user_not_found(real_auth_service, monkeypatch):

    monkeypatch.setattr(
        real_auth_service.user_repo,
        "find_by_email",
        lambda x: None
    )

    result = real_auth_service.request_password_reset("x@test.com")

    assert "If the email exists" in result["message"]

def test_request_password_reset_success(real_auth_service, monkeypatch):

    user = SimpleNamespace(id="u1")

    calls = {}

    monkeypatch.setattr(
        real_auth_service.user_repo,
        "find_by_email",
        lambda x: user
    )

    monkeypatch.setattr(
        real_auth_service.password_reset_repo,
        "create",
        lambda token: calls.update({"created": token})
    )

    result = real_auth_service.request_password_reset("user@test.com")

    assert result["message"] == "Reset email sent"
    assert "reset_token" in result
    assert calls["created"] is not None

