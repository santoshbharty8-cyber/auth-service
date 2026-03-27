import uuid
from unittest.mock import Mock
from app.services.auth_service import AuthService


# -----------------------------
# Fake dependencies
# -----------------------------
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
    def __init__(self):
        self.providers = {}

    def get_provider(self, method):
        return self.providers.get(method)


class FakeMFAChallenge:

    def check_attempts(self, token):
        return True

    def verify_challenge(self, token):
        import uuid
        return uuid.uuid4()

    def increment_attempt(self, token):   # ✅ ADD THIS
        return True

    def delete_challenge(self, token):   # ✅ ADD THIS (used in success flow)
        return True


class FakeOAuthRepo:
    pass


class FakeDeviceRepo:
    def find_device(self, user_id, fingerprint):
        return None

    def create_device(self, *args, **kwargs):
        pass


class FakeTOTPRepo:
    def find_by_user_id(self, user_id):
        return None
    
    def find_by_user(self, user_id):
        return None


class FakeRecoveryCodeRepo:
    def find_by_user_id(self, user_id):
        return []


# -----------------------------
# Factory
# -----------------------------
def create_auth_service():
    return AuthService(
        user_repo=FakeUserRepo(),
        session_repo=FakeSessionRepo(),
        audit_service=FakeAuditService(),
        password_reset_repo=FakePasswordResetRepo(),
        email_verification_repo=FakeEmailVerificationRepo(),
        provider_registry=FakeProviderRegistry(),
        mfa_challenge=FakeMFAChallenge(),
        oauth_repo=FakeOAuthRepo(),
        device_repo=FakeDeviceRepo(),
        totp_repo=FakeTOTPRepo(),
        recovery_code_repo=FakeRecoveryCodeRepo(),
    )