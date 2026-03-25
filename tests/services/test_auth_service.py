import uuid

from app.services.auth_service import AuthService


# ----------------------------------------
# FAKE REPOSITORIES
# ----------------------------------------

class FakeUserRepo:

    def __init__(self):
        self.users = {}

    def exists_by_email(self, email):
        return email in self.users

    def create(self, user):
        user.id = uuid.uuid4()   # ✅ IMPORTANT FIX
        self.users[user.email] = user
        return user


class FakeSessionRepo:

    def create(self, session):
        return session

    def find_by_hash(self, token_hash):
        return None

    def revoke(self, session):
        pass

    def revoke_all_for_user(self, user_id):
        pass

    def find_active_by_user(self, user_id):
        return []


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

    def get_provider(self, method):
        return None


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