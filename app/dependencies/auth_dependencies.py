from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_db

from app.services.auth_service import AuthService
from app.services.audit_service import AuditService
from app.services.mfa_challenge_service import MFAChallengeService
from app.services.recovery_code_service import RecoveryCodeService

from app.repositories.user_repository import UserRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.audit_repository import AuditRepository
from app.repositories.password_reset_repository import PasswordResetRepository
from app.repositories.email_verification_repository import EmailVerificationRepository
from app.repositories.oauth_repository import OAuthRepository
from app.repositories.device_repository import DeviceRepository
from app.repositories.totp_repository import TOTPRepository
from app.repositories.recovery_code_repository import RecoveryCodeRepository

from app.auth_providers.registry import AuthProviderRegistry
from app.auth_providers.password_provider import PasswordAuthProvider
from app.auth_providers.otp_provider import OTPAuthProvider
from app.auth_providers.google_oauth_provider import GoogleOAuthProvider
from app.auth_providers.github_oauth_provider import GitHubOAuthProvider
# from app.auth_providers.microsoft_oauth_provider import MicrosoftOAuthProvider


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:

    # repositories
    user_repo = UserRepository(db)
    session_repo = SessionRepository(db)
    password_reset_repo = PasswordResetRepository(db)
    email_verification_repo = EmailVerificationRepository(db)
    oauth_repo = OAuthRepository(db)
    device_repo = DeviceRepository(db)
    totp_repo = TOTPRepository(db)
    recovery_code_repo = RecoveryCodeRepository(db)

    # services
    audit_service = AuditService()
    mfa_challenge = MFAChallengeService()

    # -----------------------------
    # Auth Provider Registry
    # -----------------------------

    provider_registry = AuthProviderRegistry()
    

    provider_registry.register(
        "password",
        PasswordAuthProvider(user_repo)
    )
    
    provider_registry.register(
        "otp",
        OTPAuthProvider(user_repo)
    )
    
    provider_registry.register(
        "google_oauth",
        GoogleOAuthProvider(user_repo, oauth_repo),
    )
    
    provider_registry.register(
        "github_oauth",
        GitHubOAuthProvider(user_repo, oauth_repo)
    )
    
    # provider_registry.register(
    #     "microsoft_oauth",
    #     MicrosoftOAuthProvider()
    # )

    # -----------------------------
    # AuthService
    # -----------------------------

    return AuthService(
        user_repo=user_repo,
        session_repo=session_repo,
        audit_service=audit_service,
        mfa_challenge=mfa_challenge,
        password_reset_repo=password_reset_repo,
        email_verification_repo=email_verification_repo,
        provider_registry=provider_registry,
        oauth_repo=oauth_repo,
        device_repo=device_repo,
        totp_repo=totp_repo,
        recovery_code_repo=recovery_code_repo
    )

def get_recovery_code_service(db: Session = Depends(get_db)):

    repo = RecoveryCodeRepository(db)

    return RecoveryCodeService(repo)