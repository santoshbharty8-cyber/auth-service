from unittest.mock import Mock
from app.services.auth_service import AuthService


# -----------------------------
# Fake dependencies
# -----------------------------
class FakeUserRepo:
    def find_by_id(self, user_id):
        user = Mock()
        user.id = user_id
        return user

    def find_by_email(self, email):
        return None


class FakeSessionRepo:
    def create(self, session):
        pass


class FakeAuditService:
    def enqueue_event(self, *args, **kwargs):
        pass


class FakePasswordResetRepo:
    pass


class FakeEmailVerificationRepo:
    pass


class FakeProviderRegistry:
    pass


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