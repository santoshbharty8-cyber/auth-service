from typing import Annotated, Union

from google.oauth2 import id_token
from google.auth.transport import requests

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.cache.redis_client import redis_client
from app.security.dependencies import get_current_user
from app.security.device_fingerprint import generate_device_fingerprint
from app.security.oauth_state import create_oauth_state, validate_oauth_state
from app.security.oauth_helper import OAuthHelper

from app.repositories.session_repository import SessionRepository
from app.repositories.totp_repository import TOTPRepository
from app.repositories.recovery_code_repository import RecoveryCodeRepository
from app.dependencies.auth_dependencies import get_auth_service, get_recovery_code_service


from app.services.auth_service import AuthService
from app.services.otp_service import OTPService
from app.services.sms_service import SMSService
from app.services.totp_service import TOTPService
from app.services.recovery_code_service import RecoveryCodeService

from app.models import AuditLog, User
from app.models.totp_credential import TOTPCredential
from app.models.oauth_account import OAuthAccount
from app.rbac.dependencies import require_permission
from app.schemas.auth_schema import (
    RegisterRequest,
    RegisterResponse,
    LoginRequest,
    TokenResponse,
    RefreshRequest,
    UserOut,
    ResetConfirm,
    ResetRequest,
    VerifyEmail,
    ResendVerificationRequest,
    OTPResponse,
    LoginOTPRequest,
    RequestOTPRequest,
    LoginResponse,
    LoginPhoneOTPRequest,
    RequestPhoneOTPRequest,
    Login2FARequest,
    TwoFactorRequiredResponse,
    RecoveryCodeLoginRequest,
)

router = APIRouter()
security = HTTPBearer()
otp_service = OTPService()
sms_service = SMSService()


# AUTHService = Annotated[AuthService, Depends(get_auth_service)]



@router.post("/login", response_model=Union[TokenResponse, TwoFactorRequiredResponse])
def login(
    body: LoginRequest, 
    request: Request, 
    response: Response,
    service: AuthService = Depends(get_auth_service),
    ):
    
    user_agent = request.headers.get("user-agent")
    ip_address = (
        request.headers.get("x-forwarded-for")
        or (request.client.host if request.client else None)
        or "127.0.0.1"
    )

    return service.login(
        email=body.email,
        password=body.password,
        user_agent=user_agent,
        ip_address=ip_address
    )

@router.post("/register", response_model=RegisterResponse)
def register(request: RegisterRequest, service: AuthService = Depends(get_auth_service),):

    try:
        result = service.register(
            email=request.email,
            password=request.password,
        )
        user = result["user"]
        verification_token = result["verification_token"]
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return RegisterResponse(
        id=str(user.id),
        email=user.email,
        status=user.status,
        verification_token=verification_token
    )

@router.post("/refresh", response_model=TokenResponse)
def refresh(request: RefreshRequest, service: AuthService = Depends(get_auth_service),):

    return service.refresh(request.refresh_token)

@router.post("/logout")
def logout(
    request: RefreshRequest,
    service: AuthService = Depends(get_auth_service),
    credentials: HTTPAuthorizationCredentials = Depends(security),     
    ):
    
    access_token = credentials.credentials

    return service.logout(
        request.refresh_token,
        access_token=access_token
        )

@router.get("/me", response_model=UserOut, tags=["users"])
def get_me(
    request: Request,
    response: Response,
    current_user = Depends(get_current_user)
    ):
    return current_user

@router.post("/force-logout-all")
def force_logout_all(
    service: AuthService = Depends(get_auth_service),
    current_user=Depends(get_current_user),
):

    return service.force_logout_all(current_user.id)

@router.get("/sessions")
def list_sessions(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session_repo = SessionRepository(db)
    sessions = session_repo.find_active_by_user(current_user.id)

    return [
        {
            "id": str(s.id),
            "ip": s.ip_address,
            "user_agent": s.user_agent,
            "last_active": s.last_active_at
        }
        for s in sessions
    ]

@router.delete("/sessions/{session_id}")
def revoke_session(
    session_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session_repo = SessionRepository(db)

    session = session_repo.find_by_id(session_id)

    if session.user_id != current_user.id:
        raise HTTPException(status_code=403)

    session_repo.revoke(session)

    return {"message": "Session revoked"}

@router.get("/audit-logs")
def get_audit_logs(
    current_user: Annotated[User, Depends(require_permission("admin:access"))],
    db: Session = Depends(get_db),
):
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(100).all()

    return logs

@router.post("/password-reset/request")
def request_password_reset(body: ResetRequest, service: AuthService = Depends(get_auth_service),):

    return service.request_password_reset(body.email)

@router.post("/password-reset/confirm")
def reset_password(body: ResetConfirm, service: AuthService = Depends(get_auth_service),):

    return service.reset_password(
        token=body.token,
        new_password=body.new_password
    )

@router.post("/verify-email")
def verify_email(body: VerifyEmail, service: AuthService = Depends(get_auth_service),):

    return service.verify_email(
        token=body.token
    )

@router.post("/resend-verification")
def resend_verification(
    request: ResendVerificationRequest,
    service: AuthService = Depends(get_auth_service),
):
  
    result = service.resend_verification(request.email)    

    return {
        "message": "Verification email sent",
        "verification_token": result["verification_token"]
    }

@router.post("/request-otp", response_model=OTPResponse)
def request_otp(data: RequestOTPRequest, request: Request):

    identifier = f"email:{data.email}"
    
    # Rate limit check
    if not otp_service.rate_limit(identifier):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many OTP requests. Please try later.",
        )
    
    user_agent = request.headers.get("user-agent")
    ip = (
        request.headers.get("x-forwarded-for")
        or (request.client.host if request.client else None)
        or "127.0.0.1"
    )
    
    fingerprint = generate_device_fingerprint(user_agent, ip)

    otp = otp_service.generate_otp(identifier, fingerprint, ip)

    # TODO: Send OTP via email service
    # email_service.send_otp(data.email, otp)
    print(otp)

    return OTPResponse(message="OTP sent successfully")


@router.post("/login-otp", response_model=Union[LoginResponse, TwoFactorRequiredResponse])
def login_with_otp(
    data: LoginOTPRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
):

    
    user_agent = request.headers.get("user-agent")
    ip = (
        request.headers.get("x-forwarded-for")
        or (request.client.host if request.client else None)
        or "127.0.0.1"
    )
    
    fingerprint = generate_device_fingerprint(user_agent, ip)

    # Authenticate user via provider system
    user = service.authenticate(
        "otp",
        {
            "email": data.email,
            "otp": data.otp,
            "fingerprint": fingerprint,
            "ip": ip
        },
    )

    if service.require_2fa(user):
        mfa_token = service.mfa_challenge.create_challenge(user.id)

        return {
            "require_2fa": True,
            "mfa_token": mfa_token
        }
    
    tokens = service.create_session(
        user,
        user_agent=user_agent,
        ip_address=ip,
    )

    return LoginResponse(**tokens)


@router.get("/oauth/google/login")
def google_login(service: AuthService = Depends(get_auth_service)):

    url = service.start_google_oauth(flow="login")

    return RedirectResponse(url)

@router.get("/oauth/google/callback")
def google_callback(
    code: str,
    state: str,
    request: Request,
    service: AuthService = Depends(get_auth_service),
):
    
    state_data = OAuthHelper.consume_state(
        redis_client,
        state
    )

    if not state_data:
        raise HTTPException(
            status_code=400,
            detail="Invalid OAuth state"
        )

    payload = service.exchange_google_code(
        code,
        state_data["code_verifier"]
    )
    
    flow = state_data["flow"]

    # LOGIN FLOW
    if flow == "login":

        return service.handle_oauth_login(
            payload,
            request.headers.get("user-agent"),
            request.client.host
        )

    # LINK FLOW
    if flow == "link":

        user_id = state_data["user_id"]

        return service.link_google_account(
            user_id,
            payload
        )

    raise HTTPException(400, "Invalid OAuth flow")

@router.get("/oauth/google/link/start")
def start_link_google(
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
):

    url = service.start_google_oauth(
        flow="link",
        user_id=str(current_user.id)
    )

    return RedirectResponse(url)

@router.get("/oauth/github/login")
def github_login(service: AuthService = Depends(get_auth_service)):

    url = service.start_github_oauth(flow="login")

    return RedirectResponse(url)

@router.get("/oauth/github/callback")
async def github_callback(
    code: str,
    state: str,
    request: Request,
    service: AuthService = Depends(get_auth_service),
):

    state_data = OAuthHelper.consume_state(redis_client, state)

    if not state_data:
        raise HTTPException(
            status_code=400,
            detail="Invalid OAuth state"
        )

    provider = service.provider_registry.get_provider("github_oauth")

    # PKCE verifier
    code_verifier = state_data.get("code_verifier")

    try:
        token = await provider.exchange_code(code, code_verifier)
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid OAuth credentials"
        )

    # fetch GitHub user
    profile = await provider.fetch_user(token)

    # fetch email
    email = await provider.fetch_email(token)

    payload = {
        "provider_user_id": str(profile["id"]),
        "email": email,
        "name": profile.get("name"),
        "picture": profile.get("avatar_url")
    }

    flow = state_data["flow"]

    # LOGIN FLOW
    if flow == "login":

        user = service.handle_github_oauth_login(
            provider="github",
            payload=payload
        )
        
        if service.require_2fa(user):
            mfa_token = service.mfa_challenge.create_challenge(user.id)

            return {
                "require_2fa": True,
                "mfa_token": mfa_token
            }

        return service.create_session(
            user=user,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host
        )

    # LINK FLOW
    if flow == "link":

        user_id = state_data["user_id"]

        return service.link_github_account(
            user_id=user_id,
            payload=payload
        )

    raise HTTPException(
        status_code=400,
        detail="Invalid OAuth flow"
    )

@router.get("/oauth/github/link/start")
def github_link_start(
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
):

    url = service.start_github_oauth(
        flow="link",
        user_id=str(current_user.id)
    )

    return RedirectResponse(url)

# Implementation pending
# @router.get("/oauth/microsoft/login")
# def microsoft_login(service: AuthService = Depends(get_auth_service)):

#     url = service.start_microsoft_oauth(flow="login")

#     return RedirectResponse(url)

# @router.get("/oauth/microsoft/link/start")
# def microsoft_link_start(
#     current_user: User = Depends(get_current_user),
#     service: AuthService = Depends(get_auth_service),
# ):

#     url = service.start_microsoft_oauth(
#         flow="link",
#         user_id=str(current_user.id)
#     )

#     return RedirectResponse(url)

# @router.get("/oauth/microsoft/callback")
# async def microsoft_callback(
    # code: str,
    # state: str,
    # request: Request,
    # service: AuthService = Depends(get_auth_service),
# ):

#     state_data = OAuthHelper.consume_state(redis_client, state)

#     if not state_data:
#         raise HTTPException(400, "Invalid OAuth state")

#     provider = service.provider_registry.get_provider("microsoft_oauth")

#     token_data = await provider.exchange_code(
#         code,
#         state_data["code_verifier"]
#     )

#     payload = provider.decode_id_token(token_data["id_token"])

#     email = payload.get("email") or payload.get("preferred_username")

#     oauth_payload = {
#         "provider_user_id": payload["sub"],
#         "email": email,
#         "name": payload.get("name"),
#         "picture": None
#     }

#     flow = state_data["flow"]

#     if flow == "login":

#         user = service.handle_microsoft_oauth_login(
#             provider="microsoft",
#             payload=oauth_payload
#         )

#         return service.create_session(
#             user,
#             user_agent=request.headers.get("user-agent"),
#             ip_address=request.client.host
#         )

#     if flow == "link":

#         return service.link_oauth_account(
#             state_data["user_id"],
#             provider="microsoft",
#             payload=oauth_payload
#         )

@router.post("/magic-link")
def request_magic_link(
    email: str,
    request: Request,
    service: AuthService = Depends(get_auth_service)
):

    return service.request_magic_link(
        email,
        request.headers.get("user-agent"),
        request.client.host
    )


@router.get("/magic-login")
def magic_login(
    token: str,
    request: Request,
    service: AuthService = Depends(get_auth_service)
):

    return service.login_with_magic_link(
        token,
        request.headers.get("user-agent"),
        request.client.host
    )


@router.get("/approve-login")
def approve_login(
    request_id: str,
    request: Request,
    service: AuthService = Depends(get_auth_service)
):

    return service.approve_login(
        request_id,
        request.headers.get("user-agent"),
        request.client.host
    )


@router.post("/request-phone-otp")
def request_phone_otp(data: RequestPhoneOTPRequest, request: Request):

    identifier = f"phone:{data.phone}"

    if not otp_service.rate_limit(identifier):

        raise HTTPException(
            status_code=429,
            detail="Too many OTP requests"
        )

    user_agent = request.headers.get("user-agent")

    ip = (
        request.headers.get("x-forwarded-for")
        or (request.client.host if request.client else None)
        or "127.0.0.1"
    )

    fingerprint = generate_device_fingerprint(
        user_agent,
        ip
    )

    otp = otp_service.generate_otp(
        identifier,
        fingerprint,
        ip
    )

    # send via Twilio
    sms_service.send_otp(data.phone, otp)

    return {
        "message": "OTP sent successfully"
    }

@router.post("/login-phone-otp")
def login_phone_otp(
    data: LoginPhoneOTPRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
):

    identifier = f"phone:{data.phone}"

    user_agent = request.headers.get("user-agent")

    ip = (
        request.headers.get("x-forwarded-for")
        or (request.client.host if request.client else None)
        or "127.0.0.1"
    )

    fingerprint = generate_device_fingerprint(
        user_agent,
        ip
    )

    valid = otp_service.verify_otp(
        identifier,
        data.otp,
        fingerprint,
        ip
    )

    if not valid:
        raise HTTPException(
            status_code=400,
            detail="Invalid OTP"
        )   

    user = service.user_repo.find_by_phone(data.phone)

    if not user:
        user = service.user_repo.create_phone_user(data.phone)
    
    if service.require_2fa(user):
        mfa_token = service.mfa_challenge.create_challenge(user.id)

        return {
            "require_2fa": True,
            "mfa_token": mfa_token
        }

    tokens = service.create_session(
        user,
        user_agent=user_agent,
        ip_address=ip
    )

    return LoginResponse(**tokens)

@router.post("/2fa/setup")
def setup_2fa(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):

    totp_repo = TOTPRepository(db)

    toto_service = TOTPService()

    secret = toto_service.generate_secret()

    credential = totp_repo.create(
        TOTPCredential(
            user_id=current_user.id,
            secret=secret
        )
    )

    uri = toto_service.build_uri(
        current_user.email,
        secret
    )

    qr = toto_service.generate_qr(uri)

    return {
        "secret": secret,
        "qr_code": qr
    }


@router.post("/2fa/verify")
def verify_2fa(
    code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    recovery_code_service: RecoveryCodeService = Depends(get_recovery_code_service),
):

    totp_repo = TOTPRepository(db)

    toto_service = TOTPService()

    credential = totp_repo.find_by_user(current_user.id)

    if not credential:
        raise HTTPException(404, "2FA not setup")

    if not toto_service.verify(credential.secret, code):
        raise HTTPException(400, "Invalid code")

    totp_repo.enable(credential)
    codes = recovery_code_service.generate_codes(current_user.id)

    return {"message": "2FA enabled", "recovery_codes": codes}

@router.post("/2fa/login")
def login_2fa(
    data: Login2FARequest,
    request: Request,
    db: Session = Depends(get_db),
    service: AuthService = Depends(get_auth_service),
):

    totp_repo = TOTPRepository(db)
    totp_service = TOTPService()
    
    if not service.mfa_challenge.check_attempts(data.mfa_token):

        raise HTTPException(
            status_code=429,
            detail="Too many 2FA attempts"
        )
        
    user_id = service.mfa_challenge.verify_challenge(data.mfa_token)
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired MFA challenge"
        )
    

    user = service.user_repo.find_by_id(user_id)

    credential = totp_repo.find_by_user(user_id)

    if not credential or not credential.is_enabled:
        raise HTTPException(400, "2FA not enabled")

    valid = totp_service.verify(
        credential.secret,
        data.code
    )

    if not valid:
        service.mfa_challenge.increment_attempt(data.mfa_token)

        raise HTTPException(
            status_code=401,
            detail="Invalid 2FA code"
        )
        

    user_agent = request.headers.get("user-agent")

    ip = (
        request.headers.get("x-forwarded-for")
        or (request.client.host if request.client else None)
        or "127.0.0.1"
    )
    service.mfa_challenge.delete_challenge(data.mfa_token)

    tokens = service.create_session(
        user,
        user_agent=user_agent,
        ip_address=ip
    )

    return tokens

@router.post("/2fa/recovery-codes")
def generate_recovery_codes(
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
    recovery_code_service: RecoveryCodeService = Depends(get_recovery_code_service),
):

    # delete existing codes
    service.recovery_code_repo.delete_by_user(current_user.id)

    codes = recovery_code_service.generate_codes(current_user.id)

    return {
        "recovery_codes": codes
    }

@router.post("/2fa/recovery")
def login_with_recovery_code(
    data: RecoveryCodeLoginRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
    recovery_code_service: RecoveryCodeService = Depends(get_recovery_code_service),
):

    # -----------------------------
    # 1️⃣ Check attempt limits
    # -----------------------------

    if not service.mfa_challenge.check_attempts(data.mfa_token):
        raise HTTPException(
            status_code=429,
            detail="Too many 2FA attempts"
        )

    # -----------------------------
    # 2️⃣ Verify MFA challenge
    # -----------------------------

    user_id = service.mfa_challenge.verify_challenge(data.mfa_token)

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired MFA challenge"
        )

    user = service.user_repo.find_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # -----------------------------
    # 3️⃣ Verify recovery code
    # -----------------------------

    valid = recovery_code_service.verify_code(
        user_id,
        data.recovery_code
    )

    if not valid:

        service.mfa_challenge.increment_attempt(data.mfa_token)

        raise HTTPException(
            status_code=401,
            detail="Invalid recovery code"
        )

    # -----------------------------
    # 4️⃣ Success → delete challenge
    # -----------------------------

    service.mfa_challenge.delete_challenge(data.mfa_token)

    user_agent = request.headers.get("user-agent")
    ip_address = (
        request.headers.get("x-forwarded-for")
        or (request.client.host if request.client else None)
        or "127.0.0.1"
    )

    # -----------------------------
    # 5️⃣ Create session
    # -----------------------------

    tokens = service.create_session(
        user,
        user_agent=user_agent,
        ip_address=ip_address
    )

    return tokens

@router.post("/2fa/regenerate-recovery-codes")
def regenerate_codes(
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
    recovery_code_service: RecoveryCodeService = Depends(get_recovery_code_service),
):
    service.recovery_code_repo.delete_by_user(current_user.id)

    codes = recovery_code_service.generate_codes(current_user.id)

    return {"recovery_codes": codes}