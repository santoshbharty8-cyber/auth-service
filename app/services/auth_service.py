import uuid
import time
import json
from datetime import datetime, timedelta, UTC
from jose import jwt, JWTError, ExpiredSignatureError
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from app.core.config import settings

from app.auth_providers.registry import AuthProviderRegistry
from app.security.token_blacklist import blacklist_token
from app.security.password import verify_password, hash_password
from app.security.jwt import create_access_token, decode_access_token
from app.security.oauth_helper import OAuthHelper
from app.security.device_fingerprint import generate_device_fingerprint
from app.security.magic_link_jwt import create_magic_link_token, verify_magic_link_token

from app.models import User, RefreshToken
from app.models.password_reset_token import PasswordResetToken
from app.models.user_session import UserSession
from app.models.email_verification_token import EmailVerificationToken
from app.models.oauth_account import OAuthAccount

from app.repositories.user_repository import UserRepository
from app.repositories.token_repository import TokenRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.password_reset_repository import PasswordResetRepository
from app.repositories.email_verification_repository import EmailVerificationRepository
from app.repositories.oauth_repository import OAuthRepository
from app.repositories.device_repository import DeviceRepository
from app.repositories.totp_repository import TOTPRepository
from app.repositories.recovery_code_repository import RecoveryCodeRepository

from app.security.token_utils import generate_refresh_token, hash_token
from app.services.audit_service import AuditService
from app.services.mfa_challenge_service import MFAChallengeService
from app.cache.redis_client import redis_client
from app.utils.oauth_config import get_oauth_redirect_uri



class AuthService:

    def __init__(
        self, 
        user_repo: UserRepository, 
        session_repo: SessionRepository,
        audit_service: AuditService,
        mfa_challenge: MFAChallengeService,
        password_reset_repo: PasswordResetRepository,
        email_verification_repo: EmailVerificationRepository,
        provider_registry: AuthProviderRegistry,
        oauth_repo: OAuthRepository,
        device_repo: DeviceRepository,
        totp_repo: TOTPRepository, 
        recovery_code_repo: RecoveryCodeRepository,
        ):
        
        self.user_repo = user_repo
        self.session_repo = session_repo
        self.audit_service = audit_service
        self.mfa_challenge = mfa_challenge
        self.password_reset_repo = password_reset_repo
        self.email_verification_repo = email_verification_repo
        self.provider_registry = provider_registry
        self.oauth_repo = oauth_repo
        self.device_repo = device_repo
        self.totp_repo = totp_repo
        self.recovery_code_repo = recovery_code_repo
    
    
    def authenticate(self, method: str, request_data: dict):

        provider = self.provider_registry.get_provider(method)

        if not provider:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported authentication method: {method}"
            )

        user = provider.authenticate(request_data)

        # if not user:
        #     raise HTTPException(
        #         status_code=status.HTTP_401_UNAUTHORIZED,
        #         detail="Authentication failed"
        #     )

        return user

    def login(self, email: str, password: str, user_agent: str, ip_address: str):

        user = self.user_repo.find_by_email(email)
        now = datetime.now(UTC)

        if not user:
            self.audit_service.enqueue_event(
                event_type="LOGIN",
                event_status="FAILURE",
                metadata={"reason": "user_not_found", "email": email},
                ip_address=ip_address,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        
        # NEW: Email verification check
        if user.status != "ACTIVE":
            self.audit_service.enqueue_event(
                event_type="LOGIN",
                event_status="FAILURE",
                user_id=user.id,
                metadata={"reason": "email_not_verified"},
                ip_address=ip_address,
            )

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email not verified"
            )
        
        if user.locked_until:
            locked_until = user.locked_until

            # SQLite safety: normalize if tz missing
            if locked_until.tzinfo is None:
                locked_until = locked_until.replace(tzinfo=UTC)

            if locked_until > now:
                raise HTTPException(
                    status_code=403,
                    detail="Account locked. Try later."
                )

        auth_user = self.authenticate(
            "password",
            {
                "email": email,
                "password": password
            }
        )
        
        if not auth_user:

            user.failed_attempts += 1            

            if user.failed_attempts >= settings.MAX_LOGIN_ATTEMPTS:
                user.locked_until = now + timedelta(
                    minutes=settings.LOCKOUT_MINUTES
                )

            self.user_repo.save(user)
            remaining_attempts = settings.MAX_LOGIN_ATTEMPTS - user.failed_attempts

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Incorrect username or password. {remaining_attempts} attempt(s) remaining."
            )
        
        user.failed_attempts = 0
        user.locked_until = None
        self.user_repo.save(user)
        
        if self.require_2fa(user):
            mfa_token = self.mfa_challenge.create_challenge(user.id)

            return {
                "require_2fa": True,
                "mfa_token": mfa_token
            }
        
        return self.create_session(
            user=user,
            user_agent=user_agent,
            ip_address=ip_address
        )
    
    def register(self, email: str, password: str):        

        if self.user_repo.exists_by_email(email):
            self.audit_service.enqueue_event(
                event_type="REGISTER",
                event_status="FAILURE",
                metadata={"email": email},
            )
            raise HTTPException(
                status_code=400,
                detail="Email already registered",
            )

        user = User(
            email=email,
            password_hash=hash_password(password),
            status="PENDING"
        )
     
        created_user = self.user_repo.create(user)
        
        # Generate verification token
        verification_token = str(uuid.uuid4())

        token_hash = hash_token(verification_token)

        verification = EmailVerificationToken(
            user_id=created_user.id,
            token_hash=token_hash,
            expires_at=datetime.now(UTC) + timedelta(hours=24)
        )

        self.email_verification_repo.create(verification)

        verification_link = f"{settings.BASE_URL}/verify-email?token={verification_token}"

        print("Verification link:", verification_link)

        self.audit_service.enqueue_event(
            event_type="REGISTER",
            event_status="SUCCESS",
            user_id=created_user.id,
        )

        return {
            "user": created_user,
            "verification_token": verification_token,
            "link": verification_link
        }        
    
    def refresh(self, refresh_token: str):

        token_hash = hash_token(refresh_token)
        
        session = self.session_repo.find_by_hash(token_hash)

        if not session:
            self.audit_service.enqueue_event(
                event_type="REFRESH",
                event_status="FAILURE",
                metadata={"reason": "invalid_refresh"},
            )
            # Possible reuse attack
            raise HTTPException(status_code=403, detail="Invalid refresh token")

        user = self.user_repo.find_by_id(session.user_id)

        new_refresh = generate_refresh_token()
        new_hash = hash_token(new_refresh)
        
        session.refresh_token_hash = new_hash
        session.last_active_at = datetime.now(UTC)
        
        self.session_repo.save(session)

        new_access = create_access_token(
            {"sub": str(user.id)},
            token_version=user.token_version,
        )

        self.audit_service.enqueue_event(
            event_type="REFRESH",
            event_status="SUCCESS",
            user_id=user.id,
        )
        return {
            "access_token": new_access,
            "refresh_token": new_refresh
        }
    
    def logout(self, refresh_token: str, access_token: str):

        token_hash = hash_token(refresh_token)
        print("token_hash - ", token_hash)
        # stored_token = self.token_repo.find_by_hash(token_hash)
        session = self.session_repo.find_by_hash(token_hash)
        print("session - ", session)
        

        if not session:
            raise HTTPException(
                status_code=400,
                detail="Invalid refresh token"
            )

        self.session_repo.revoke(session)        
        
        try:
            payload = decode_access_token(access_token)

            jti = payload.get("jti")
            exp = payload.get("exp")

            if not jti or not exp:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid access token",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # Calculate remaining TTL
            now_ts = int(datetime.now(UTC).timestamp())
            ttl = int(exp - now_ts)

            if ttl > 0:
                blacklist_token(jti, ttl)

        except ExpiredSignatureError:
            # If access token already expired, nothing to blacklist
            pass

        except JWTError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid access token",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

        self.audit_service.enqueue_event(
            event_type="LOGOUT",
            event_status="SUCCESS",
            user_id=session.user_id,
        )
        return {"message": "Logged out successfully"}
    
    def force_logout_all(self, user_id: str):

        user = self.user_repo.find_by_id(user_id)

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user.token_version += 1
        self.user_repo.save(user)

        # Deactivate all device sessions
        self.session_repo.revoke_all_for_user(user_id)

        self.audit_service.enqueue_event(
            event_type="FORCE_LOGOUT_ALL",
            event_status="SUCCESS",
            user_id=user_id,
        )

        return {"message": "All sessions invalidated"}
    
    def request_password_reset(self, email: str):

        user = self.user_repo.find_by_email(email)

        if not user:
            return {"message": "If the email exists, a reset link was sent"}

        reset_token = str(uuid.uuid4())

        token_hash = hash_token(reset_token)

        token = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.now(UTC) + timedelta(minutes=30),
        )

        self.password_reset_repo.create(token)

        # send email here
        reset_link = f"{settings.BASE_URL}/reset-password?token={reset_token}"

        print("Reset link:", reset_link)

        return {
            "message": "Reset email sent",
            "reset_token": reset_token,
            "link": reset_link
        }   


    def reset_password(self, token: str, new_password: str):

        token_hash = hash_token(token)

        reset_token = self.password_reset_repo.find_by_hash(token_hash)

        if not reset_token:
            raise HTTPException(status_code=400, detail="Invalid reset token")

        expires_at = reset_token.expires_at
        
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)

        if expires_at < datetime.now(UTC):
            raise HTTPException(status_code=400, detail="Reset token expired")
        user = self.user_repo.find_by_id(reset_token.user_id)

        # update password
        user.password_hash = hash_password(new_password)

        # invalidate all access tokens
        user.token_version += 1

        self.user_repo.save(user)

        # deactivate sessions
        self.session_repo.revoke_all_for_user(user.id)

        # delete reset token
        self.password_reset_repo.delete(reset_token)

        return {"message": "Password updated successfully"}
    
    def verify_email(self, token: str):

        token_hash = hash_token(token)

        verification = self.email_verification_repo.find_by_hash(token_hash)

        if not verification:
            raise HTTPException(status_code=400, detail="Invalid token")

        expires_at = verification.expires_at

        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)

        if expires_at < datetime.now(UTC):
            raise HTTPException(status_code=400, detail="Token expired")

        user = self.user_repo.find_by_id(verification.user_id)

        user.status = "ACTIVE"

        self.user_repo.save(user)

        self.email_verification_repo.delete(verification)

        return {"message": "Email verified successfully"}
    
    def resend_verification(self, email: str):

        user = self.user_repo.find_by_email(email)

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        if user.status == "ACTIVE":
            raise HTTPException(
                status_code=400,
                detail="Account already verified"
            )

        # remove old tokens
        self.email_verification_repo.delete_by_user_id(user.id)

        verification_token = str(uuid.uuid4())
        token_hash = hash_token(verification_token)

        verification = EmailVerificationToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.now(UTC) + timedelta(hours=24)
        )

        self.email_verification_repo.create(verification)

        verification_link = f"{settings.BASE_URL}/verify-email?token={verification_token}"

        print("Verification link:", verification_link)

        self.audit_service.enqueue_event(
            event_type="RESEND_VERIFICATION",
            event_status="SUCCESS",
            user_id=user.id
        )

        return {
            "verification_token": verification_token,
            "link": verification_link
        }
    
    
    def require_2fa(self, user):
        
        if not user:
            return False        

        credential = self.totp_repo.find_by_user(user.id)

        if credential and credential.is_enabled:
            return True

        return False
    
    def create_session(
        self,
        user: User,
        user_agent: str,
        ip_address: str
    ):

        access_token = create_access_token(
            {"sub": str(user.id)},
            token_version=user.token_version
        )

        refresh_token = generate_refresh_token()

        token_hash = hash_token(refresh_token)

        session = UserSession(
            user_id=user.id,
            refresh_token_hash=token_hash,
            user_agent=user_agent,
            ip_address=ip_address,
        )

        self.session_repo.create(session)

        self.audit_service.enqueue_event(
            event_type="LOGIN",
            event_status="SUCCESS",
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token
        }
    
    
    def start_google_oauth(self, flow: str, user_id: str | None = None):
        
        redirect_uri = get_oauth_redirect_uri("google")

        state = OAuthHelper.generate_state()

        code_verifier, challenge = OAuthHelper.generate_pkce()

        OAuthHelper.store_state(
            redis_client,
            state,
            {
                "flow": flow,
                "user_id": user_id,
                "code_verifier": code_verifier,
                "created_at": int(time.time())
            }
        )

        url = (
            f"{settings.GOOGLE_OAUTH_URL}"
            f"?client_id={settings.GOOGLE_CLIENT_ID}"
            f"&redirect_uri={redirect_uri}"
            f"&response_type=code"
            f"&scope=openid email profile"
            f"&state={state}"
            f"&code_challenge={challenge}"
            f"&code_challenge_method=S256"
        )

        return url

    
    def exchange_google_code(self, code: str, code_verifier: str):

        provider = self.provider_registry.get_provider("google_oauth")

        token_data = provider.exchange_code_for_token(
            code,
            code_verifier
        )

        payload = provider.verify_identity(token_data["id_token"])

        return payload


    def handle_oauth_login(self, payload, user_agent, ip_address):

        provider_user_id = payload["sub"]

        oauth_account = self.oauth_repo.find_by_provider_user_id(
            "google",
            provider_user_id
        )

        if not oauth_account:
            return {
                "status": "link_required",
                "email": payload["email"]
            }

        user = oauth_account.user
        
        if self.require_2fa(user):
            mfa_token = self.mfa_challenge.create_challenge(user.id)

            return {
                "require_2fa": True,
                "mfa_token": mfa_token
            }

        return self.create_session(
            user,
            user_agent=user_agent,
            ip_address=ip_address
        )


    def link_google_account(self, user_id, payload):

        provider_user_id = payload["sub"]

        existing = self.oauth_repo.find_by_provider_user_id(
            "google",
            provider_user_id
        )

        if existing:
            raise HTTPException(
                status_code=409,
                detail="Google account already linked"
            )

        oauth_account = OAuthAccount(
            user_id=user_id,
            provider="google",
            provider_user_id=provider_user_id,
            email=payload["email"],
            email_verified=True
        )

        self.oauth_repo.create(oauth_account)

        return {"message": "Google account linked successfully"}
    
    
    def handle_github_oauth_login(self, provider, payload):

        provider_user_id = payload["provider_user_id"]

        oauth_account = self.oauth_repo.find_by_provider_user_id(
            provider,
            provider_user_id
        )

        if oauth_account:
            return oauth_account.user

        user = self.user_repo.find_by_email(payload["email"])

        if user:
            raise HTTPException(
                status_code=409,
                detail="Account exists. Please link GitHub."
            )

        user = User(
            email=payload["email"],
            password_hash=None,
            status="ACTIVE"
        )

        user = self.user_repo.create(user)
        
        return user
    
    
    def start_github_oauth(self, flow: str, user_id=None):
        
        redirect_uri = get_oauth_redirect_uri("github")

        state = OAuthHelper.generate_state()

        code_verifier, challenge = OAuthHelper.generate_pkce()

        OAuthHelper.store_state(
            redis_client,
            state,
            {
                "flow": flow,
                "user_id": user_id,
                "code_verifier": code_verifier
            }
        )

        url = (
            f"{settings.GITHUB_OAUTH_URL}"
            f"?client_id={settings.AUTH_GITHUB_CLIENT_ID}"
            f"&redirect_uri={redirect_uri}"
            f"&scope=user:email"
            f"&state={state}"
            f"&code_challenge={challenge}"
            f"&code_challenge_method=S256"
        )

        return url
    
    
    
    def link_github_account(self, user_id, payload):

        provider_user_id = str(payload["provider_user_id"])

        existing = self.oauth_repo.find_by_provider_user_id(
            "github",
            provider_user_id
        )

        if existing:
            raise HTTPException(
                status_code=409,
                detail="GitHub account already linked"
            )

        oauth_account = OAuthAccount(
            user_id=user_id,
            provider="github",
            provider_user_id=provider_user_id,
            email=payload["email"],
            email_verified=True,
            name=payload.get("name"),
            picture=payload.get("avatar_url")
        )

        self.oauth_repo.create(oauth_account)

        return {"message": "GitHub account linked successfully"}
    
    # def start_microsoft_oauth(self, flow: str, user_id=None):

    #     state = OAuthHelper.generate_state()

    #     code_verifier, challenge = OAuthHelper.generate_pkce()

    #     OAuthHelper.store_state(
    #         redis_client,
    #         state,
    #         {
    #             "flow": flow,
    #             "user_id": user_id,
    #             "code_verifier": code_verifier
    #         }
    #     )

    #     url = (
    #         f"{settings.MICROSOFT_AUTH_URL}"
    #         f"?client_id={settings.MICROSOFT_CLIENT_ID}"
    #         f"&response_type=code"
    #         f"&redirect_uri={settings.MICROSOFT_REDIRECT_URI}"
    #         f"&response_mode=query"
    #         f"&scope=openid email profile"
    #         f"&state={state}"
    #         f"&code_challenge={challenge}"
    #         f"&code_challenge_method=S256"
    #     )

    #     return url
    
    # def handle_microsoft_oauth_login(self, payload):

    #     provider_user_id = payload["provider_user_id"]

    #     oauth_account = self.oauth_repo.find_by_provider_user_id(
    #         "microsoft",
    #         provider_user_id
    #     )

    #     # already linked → login
    #     if oauth_account:
    #         return oauth_account.user

    #     email = payload["email"]

    #     user = self.user_repo.find_by_email(email)

    #     # existing user but OAuth not linked
    #     if user:
    #         raise HTTPException(
    #             status_code=409,
    #             detail="Account exists. Please link Microsoft login."
    #         )

    #     # auto-register new user
    #     user = User(
    #         email=email,
    #         password_hash=None,
    #         status="ACTIVE"
    #     )

    #     user = self.user_repo.create(user)

    #     return user
    
    # def link_microsoft_account(self, user_id, payload):

    #     provider_user_id = payload["provider_user_id"]

    #     existing = self.oauth_repo.find_by_provider_user_id(
    #         "microsoft",
    #         provider_user_id
    #     )

    #     if existing:
    #         raise HTTPException(
    #             status_code=409,
    #             detail="Microsoft account already linked"
    #         )

    #     oauth_account = OAuthAccount(
    #         user_id=user_id,
    #         provider="microsoft",
    #         provider_user_id=provider_user_id,
    #         email=payload["email"],
    #         email_verified=True,
    #         name=payload.get("name"),
    #         picture=None
    #     )

    #     self.oauth_repo.create(oauth_account)

    #     return {
    #         "message": "Microsoft account linked successfully"
    #     }
    
    def request_magic_link(self, email: str, user_agent: str, ip_address: str):

        user = self.user_repo.find_by_email(email)

        if not user:
            return {"message": "If email exists, login link sent"}

        fingerprint = generate_device_fingerprint(
            user_agent,
            ip_address
        )

        token = create_magic_link_token(
            user.id,
            user.email,
            fingerprint,
            ip_address
        )

        login_link = f"{settings.BASE_URL}/auth/magic-login?token={token}"

        print("Magic link:", login_link)

        return {
            "message": "Magic login link sent",
            "token": token,
            "link": login_link
            }
    
    
    def login_with_magic_link(
        self,
        token: str,
        user_agent: str,
        ip_address: str
    ):

        payload = verify_magic_link_token(token)

        jti = payload["jti"]
        user_id = payload["sub"]

        redis_key = f"magic:{jti}"

        # replay protection (atomic)
        if not redis_client.set(redis_key, "used", nx=True, ex=600):
            raise HTTPException(status_code=400, detail="Magic link already used")

        fingerprint = generate_device_fingerprint(
            user_agent,
            ip_address
        )

        suspicious = False

        if payload["fingerprint"] != fingerprint:
            suspicious = True

        if payload["ip"] != ip_address:
            suspicious = True

        device = self.device_repo.find_device(user_id, fingerprint)

        # trusted device + normal IP → login
        if device and not suspicious:

            user = self.user_repo.find_by_id(user_id)
            
            if self.require_2fa(user):
                mfa_token = self.mfa_challenge.create_challenge(user.id)

                return {
                    "require_2fa": True,
                    "mfa_token": mfa_token
                }

            return self.create_session(
                user,
                user_agent=user_agent,
                ip_address=ip_address
            )

        # suspicious login → require approval
        request_id = str(uuid.uuid4())

        redis_client.setex(
            f"login_approval:{request_id}",
            300,
            json.dumps({
                "user_id": user_id,
                "fingerprint": fingerprint,
                "ip": ip_address
            })
        )

        approval_link = f"{settings.BASE_URL}/auth/approve-login?request_id={request_id}"

        print("Approval link:", approval_link)

        return {
            "approval_required": True,
            "approval_link": approval_link
        }
    
    
    def approve_login(
        self,
        request_id: str,
        user_agent: str,
        ip_address: str
    ):

        data = redis_client.get(f"login_approval:{request_id}")

        if not data:
            raise HTTPException(400, "Invalid or expired approval request")

        payload = json.loads(data)

        redis_client.delete(f"login_approval:{request_id}")

        user = self.user_repo.find_by_id(payload["user_id"])
        
        fingerprint = payload["fingerprint"]

        # save device
        self.device_repo.create_device(
            user.id,
            fingerprint,
            user_agent,
            ip_address
        )
        
        if self.require_2fa(user):
            mfa_token = self.mfa_challenge.create_challenge(user.id)

            return {
                "require_2fa": True,
                "mfa_token": mfa_token
            }


        return self.create_session(
            user,
            user_agent=user_agent,
            ip_address=ip_address
        )
    