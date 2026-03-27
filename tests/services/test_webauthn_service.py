import base64
import json
import uuid
from types import SimpleNamespace

import cbor2
import pytest

from app.services import webauthn_service
from app.services.webauthn_service import WebAuthnService
from app.models.webauthn_credential import WebAuthnCredential


# ----------------------------------------
# MOCK REDIS
# ----------------------------------------

class MockRedis:
    def __init__(self):
        self.store = {}

    def setex(self, key, ttl, value):
        self.store[key] = value

    def get(self, key):
        return self.store.get(key)

    def delete(self, key):
        self.store.pop(key, None)


# ----------------------------------------
# FAKE REPOS
# ----------------------------------------

class FakeWebAuthnRepo:
    def __init__(self):
        self.saved = None
        self.updated = None
        self.by_user = []
        self.by_credential = None

    def create(self, cred):
        self.saved = cred
        return cred

    def find_by_user(self, user_id):
        return self.by_user

    def find_by_credential_id(self, credential_id):
        return self.by_credential

    def update(self, cred):
        self.updated = cred
        return cred


class FakeUserRepo:
    def __init__(self):
        self.users = {}

    def find_by_id(self, user_id):
        return self.users.get(str(user_id))


# ----------------------------------------
# FIXTURES
# ----------------------------------------

@pytest.fixture
def patch_redis(monkeypatch):
    redis = MockRedis()
    monkeypatch.setattr(webauthn_service, "redis_client", redis)
    return redis


@pytest.fixture
def webauthn_service_instance():
    webauthn_repo = FakeWebAuthnRepo()
    user_repo = FakeUserRepo()
    svc = WebAuthnService(webauthn_repo, user_repo)
    return svc, webauthn_repo, user_repo


# ----------------------------------------
# TESTS
# ----------------------------------------

def test_base64_conversion(webauthn_service_instance):
    svc, *_ = webauthn_service_instance

    raw = b"hello"
    enc = svc.to_base64url(raw)

    assert isinstance(enc, str)
    assert svc.from_base64url(enc) == raw


def test_start_registration_sets_redis_and_returns_options(monkeypatch, patch_redis, webauthn_service_instance):
    svc, *_ = webauthn_service_instance

    fake_user = SimpleNamespace(id=uuid.uuid4(), email="u@example.com")

    options = {
        "publicKey": {
            "challenge": "abc",
            "rp": {"name": "Auth System", "id": "localhost"},
            "user": {
                "id": b"uid",
                "name": "u@example.com",
                "displayName": "u@example.com",
            },
            "pubKeyCredParams": [{"type": "public-key", "alg": -7}],
        }
    }

    monkeypatch.setattr(
        webauthn_service,
        "server",
        SimpleNamespace(register_begin=lambda user, user_verification: (options, {"p": 1}))
    )

    result = svc.start_registration(fake_user)

    assert "publicKey" in result
    assert patch_redis.get(f"webauthn_reg:{fake_user.id}") is not None
    assert result["publicKey"]["challenge"] == "abc"


def test_finish_registration_expiry(webauthn_service_instance):
    svc, *_ = webauthn_service_instance
    fake_user = SimpleNamespace(id=uuid.uuid4())

    with pytest.raises(Exception, match="Registration expired"):
        svc.finish_registration(fake_user, {"id": "x"})


def test_finish_registration_success(monkeypatch, patch_redis, webauthn_service_instance):
    svc, webauthn_repo, _ = webauthn_service_instance
    fake_user = SimpleNamespace(id=uuid.uuid4(), email="u@example.com")

    patch_redis.setex(
        f"webauthn_reg:{fake_user.id}",
        300,
        json.dumps({"state": "x"})
    )

    fake_cred_data = SimpleNamespace(
        credential_id=b"cred_id",
        public_key={"k": "v"},
    )

    fake_auth_data = SimpleNamespace(
        credential_data=fake_cred_data,
        counter=10
    )

    monkeypatch.setattr(
        webauthn_service,
        "server",
        SimpleNamespace(register_complete=lambda s, c: fake_auth_data)
    )

    returned = svc.finish_registration(fake_user, {"id": "ignored"})

    assert isinstance(returned, WebAuthnCredential)
    assert returned.user_id == fake_user.id
    assert webauthn_repo.saved is returned
    assert patch_redis.get(f"webauthn_reg:{fake_user.id}") is None


def test_start_login_no_credentials(webauthn_service_instance):
    svc, *_ = webauthn_service_instance
    fake_user = SimpleNamespace(id=uuid.uuid4())

    with pytest.raises(Exception, match="No passkeys registered"):
        svc.start_login(fake_user)


def test_finish_login_credential_not_found(webauthn_service_instance):
    svc, *_ = webauthn_service_instance

    with pytest.raises(Exception, match="Credential not found"):
        svc.finish_login({"id": "not-exist"})

def test_finish_login_success(monkeypatch, patch_redis, webauthn_service_instance):
    svc, webauthn_repo, user_repo = webauthn_service_instance

    user = SimpleNamespace(id=uuid.uuid4(), email="u@example.com")
    user_repo.users[str(user.id)] = user

    # ✅ FIX 1: store credential_id as base64url STRING
    def b64url(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).decode().rstrip("=")

    encoded_cred_id = b64url(b"cred1")

    cred = SimpleNamespace(
        credential_id=encoded_cred_id,
        public_key=base64.b64encode(cbor2.dumps({
            1: 2,
            3: -7,      # ✅ THIS FIXES YOUR ERROR
            -1: 1,
            -2: b"x" * 32,
            -3: b"y" * 32,
        })).decode(),
        sign_count=1,
        user_id=user.id,
    )

    webauthn_repo.by_credential = cred

    # Redis state
    patch_redis.setex(
        f"webauthn_login:{user.id}",
        300,
        base64.b64encode(json.dumps({"state": "x"}).encode()).decode()
    )

    # Mock server
    monkeypatch.setattr(
        webauthn_service,
        "server",
        SimpleNamespace(authenticate_complete=lambda *a, **k: None)
    )

    # Mock response
    monkeypatch.setattr(
        webauthn_service,
        "AuthenticationResponse",
        SimpleNamespace(
            from_dict=lambda d: SimpleNamespace(
                response=SimpleNamespace(
                    authenticator_data=SimpleNamespace(counter=2)
                )
            )
        )
    )

    # ✅ FIX 2: input must ALSO be base64url string
    credential_id = encoded_cred_id

    result = svc.finish_login({
        "id": credential_id,
        "response": {
            "authenticatorData": b64url(b"data"),
            "clientDataJSON": b64url(b"data"),
            "signature": b64url(b"sig"),
        }
    })

    assert result is user
    assert cred.sign_count == 2
    assert webauthn_repo.updated is cred
    assert patch_redis.get(f"webauthn_login:{user.id}") is None

def test_to_base64url_with_string(webauthn_service_instance):
    svc, *_ = webauthn_service_instance

    result = svc.to_base64url("hello")  # string input

    assert isinstance(result, str)

def test_start_login_success(monkeypatch, patch_redis, webauthn_service_instance):
    svc, webauthn_repo, _ = webauthn_service_instance

    user = SimpleNamespace(id=uuid.uuid4())

    # mock credential
    cred = SimpleNamespace(
        credential_id=svc.to_base64url(b"cred1")
    )
    webauthn_repo.by_user = [cred]

    # mock server response
    fake_options = SimpleNamespace(
        challenge=b"challenge",
        rp_id="localhost",
        timeout=60000,
        user_verification="preferred"
    )

    monkeypatch.setattr(
        webauthn_service,
        "server",
        SimpleNamespace(
            authenticate_begin=lambda creds: (
                SimpleNamespace(public_key=fake_options),
                {"state": "x"}
            )
        )
    )

    result = svc.start_login(user)

    assert "publicKey" in result
    assert patch_redis.get(f"webauthn_login:{user.id}") is not None

def test_finish_login_replay_attack(monkeypatch, patch_redis, webauthn_service_instance):
    svc, webauthn_repo, user_repo = webauthn_service_instance

    user = SimpleNamespace(id=uuid.uuid4())
    user_repo.users[str(user.id)] = user

    encoded_id = svc.to_base64url(b"cred1")

    cred = SimpleNamespace(
        credential_id=encoded_id,
        public_key=base64.b64encode(cbor2.dumps({
            1: 2, 3: -7, -1: 1, -2: b"x"*32, -3: b"y"*32
        })).decode(),
        sign_count=10,  # HIGH
        user_id=user.id
    )

    webauthn_repo.by_credential = cred

    patch_redis.setex(
        f"webauthn_login:{user.id}",
        300,
        base64.b64encode(json.dumps({"state": "x"}).encode()).decode()
    )

    monkeypatch.setattr(
        webauthn_service,
        "server",
        SimpleNamespace(authenticate_complete=lambda *a, **k: None)
    )

    # counter LOWER than stored → replay attack
    monkeypatch.setattr(
        webauthn_service,
        "AuthenticationResponse",
        SimpleNamespace(
            from_dict=lambda d: SimpleNamespace(
                response=SimpleNamespace(
                    authenticator_data=SimpleNamespace(counter=5)
                )
            )
        )
    )

    with pytest.raises(Exception, match="Possible cloned authenticator detected"):
        svc.finish_login({
            "id": encoded_id,
            "response": {
                "authenticatorData": svc.to_base64url(b"data"),
                "clientDataJSON": svc.to_base64url(b"data"),
                "signature": svc.to_base64url(b"sig"),
            }
        })

def test_finish_login_user_not_found(monkeypatch, patch_redis, webauthn_service_instance):
    svc, webauthn_repo, user_repo = webauthn_service_instance

    encoded_id = svc.to_base64url(b"cred1")

    cred = SimpleNamespace(
        credential_id=encoded_id,
        public_key=base64.b64encode(cbor2.dumps({
            1: 2, 3: -7, -1: 1, -2: b"x"*32, -3: b"y"*32
        })).decode(),
        sign_count=1,
        user_id=uuid.uuid4()
    )

    webauthn_repo.by_credential = cred

    patch_redis.setex(
        f"webauthn_login:{cred.user_id}",
        300,
        base64.b64encode(json.dumps({"state": "x"}).encode()).decode()
    )

    monkeypatch.setattr(
        webauthn_service,
        "server",
        SimpleNamespace(authenticate_complete=lambda *a, **k: None)
    )

    monkeypatch.setattr(
        webauthn_service,
        "AuthenticationResponse",
        SimpleNamespace(
            from_dict=lambda d: SimpleNamespace(
                response=SimpleNamespace(
                    authenticator_data=SimpleNamespace(counter=2)
                )
            )
        )
    )

    # no user in repo
    result = svc.finish_login({
        "id": encoded_id,
        "response": {
            "authenticatorData": svc.to_base64url(b"data"),
            "clientDataJSON": svc.to_base64url(b"data"),
            "signature": svc.to_base64url(b"sig"),
        }
    })

    assert result is None

def test_finish_login_expired_state(monkeypatch, webauthn_service_instance):
    svc, webauthn_repo, user_repo = webauthn_service_instance

    user = SimpleNamespace(id=uuid.uuid4())

    encoded_id = svc.to_base64url(b"cred1")

    # valid credential exists
    cred = SimpleNamespace(
        credential_id=encoded_id,
        public_key=base64.b64encode(cbor2.dumps({
            1: 2, 3: -7, -1: 1, -2: b"x"*32, -3: b"y"*32
        })).decode(),
        sign_count=1,
        user_id=user.id
    )

    webauthn_repo.by_credential = cred

    # ❌ DO NOT set Redis state → simulate expiry

    monkeypatch.setattr(
        webauthn_service,
        "server",
        SimpleNamespace(authenticate_complete=lambda *a, **k: None)
    )

    monkeypatch.setattr(
        webauthn_service,
        "AuthenticationResponse",
        SimpleNamespace(
            from_dict=lambda d: SimpleNamespace(
                response=SimpleNamespace(
                    authenticator_data=SimpleNamespace(counter=2)
                )
            )
        )
    )

    with pytest.raises(Exception, match="Login expired"):
        svc.finish_login({
            "id": encoded_id,
            "response": {
                "authenticatorData": svc.to_base64url(b"data"),
                "clientDataJSON": svc.to_base64url(b"data"),
                "signature": svc.to_base64url(b"sig"),
            }
        })