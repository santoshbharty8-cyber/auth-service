"""
🔐 Authentication API Module

This module provides all core authentication functionalities for the Auth Service.

It includes:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔐 Authentication
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- User Registration (Email & Password)
- Login with JWT (Access + Refresh Tokens)
- Logout (Token Invalidation / Blacklisting)
- Get Current User (/auth/me)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📧 Email-Based Authentication
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Email OTP Login
- OTP Verification
- Password Reset (Forgot / Reset Password)
- Email Verification Flow

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔗 Social Authentication (OAuth)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Google OAuth Login
- GitHub OAuth Login
- Account Linking (Google / GitHub)
- OAuth Callback Handling

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🛡️ Security Features
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- JWT Authentication (RS256)
- Refresh Token Rotation
- Token Blacklisting
- State Validation (OAuth CSRF Protection)
- Rate Limiting (OTP Protection)
- Secure Password Hashing (bcrypt/argon2)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ Demo Instructions (Swagger / Recruiter)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔐 Email Login:
1. POST /auth/login
2. Copy access_token
3. Click "Authorize" in Swagger
4. Call /auth/me

📧 OTP Login:
1. POST /auth/send-otp
2. Use demo OTP or Mailtrap inbox
3. POST /auth/verify-otp

🔗 Google OAuth:
👉 Open in browser:
   /auth/oauth/google/login

🔗 GitHub OAuth:
👉 Open in browser:
   /auth/oauth/github/login

⚠️ NOTE:
OAuth flows require browser redirects and cannot be completed inside Swagger UI.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏗️ Architecture Notes
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Follows Service Layer + Repository Pattern
- Stateless JWT authentication
- OAuth provider abstraction (Google, GitHub)
- Environment-based configuration (.env)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚀 Production Readiness
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Dockerized deployment (Railway)
- PostgreSQL integration
- Scalable design for microservices
- Ready for Kubernetes deployment

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from typing import Annotated, Union
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi import BackgroundTasks
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.cache.redis_client import redis_client
from app.security.dependencies import get_current_user
from app.security.device_fingerprint import generate_device_fingerprint
from app.security.oauth_helper import OAuthHelper

from app.repositories.session_repository import SessionRepository
from app.repositories.totp_repository import TOTPRepository
from app.dependencies.auth_dependencies import get_auth_service, get_recovery_code_service


from app.services.auth_service import AuthService
from app.services.otp_service import OTPService
from app.services.sms_service import SMSService
from app.services.totp_service import TOTPService
from app.services.email_service import EmailService
from app.services.recovery_code_service import RecoveryCodeService

from app.models import AuditLog, User
from app.models.totp_credential import TOTPCredential
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
email_service = EmailService()

# AUTHService = Annotated[AuthService, Depends(get_auth_service)]

def get_google_login_description():
    return f"""
👉 **Click to Login with Google:**

<a href="{settings.BASE_URL}/auth/oauth/google/login" target="_blank">
🔗 Google Login
</a>

⚠️ Note:
- Open in browser (not Swagger Try-it-out)
- OAuth requires redirect flow
"""

def get_github_login_description():
    return f"""
👉 **Click to Login with GitHub:**

<a href="{settings.BASE_URL}/auth/oauth/github/login" target="_blank">
🔗 GitHub Login
</a>

⚠️ Note:
- Open in browser (not Swagger Try-it-out)
- OAuth requires redirect flow
"""


@router.post("/login", response_model=Union[TokenResponse, TwoFactorRequiredResponse])
def login(
    body: LoginRequest, 
    request: Request, 
    response: Response,
    service: AuthService = Depends(get_auth_service),
    ):
    """
    🔐 Authenticate user using email and password.

    This endpoint validates user credentials and initiates a login session.
    Depending on the user's security settings, it may either return JWT tokens
    or require additional two-factor authentication (2FA).

    Returns JWT tokens or requires 2FA if enabled.

    Includes client metadata (IP, User-Agent) for security tracking.
    """
    
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
    """
    Register a new user.

    Creates an account and returns a verification token.

    Returns:
    - id, email, status
    - verification_token (for email verification)

    Errors:
    - 400 if email already exists or validation fails
    """

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
    """
    Refresh access token using a valid refresh token.

    Returns new JWT tokens (access + refresh).

    Notes:
    - Supports token rotation
    - Fails if token is expired or revoked
    """

    return service.refresh(request.refresh_token)

@router.post("/logout")
def logout(
    request: RefreshRequest,
    service: AuthService = Depends(get_auth_service),
    credentials: HTTPAuthorizationCredentials = Depends(security),     
    ):
    """
    Logout user by invalidating refresh and access tokens.

    Notes:
    - Blacklists tokens
    - Ends current session
    """
    
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
    """
    Get current authenticated user.

    Returns user profile from JWT context.
    """
    return current_user

@router.post("/force-logout-all")
def force_logout_all(
    service: AuthService = Depends(get_auth_service),
    current_user=Depends(get_current_user),
):
    """
    Force logout from all devices.

    Notes:
    - Revokes all active sessions
    - Invalidates all tokens
    """

    return service.force_logout_all(current_user.id)

@router.get("/sessions")
def list_sessions(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List active user sessions.

    Includes IP, device (User-Agent), and last activity.
    """
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
    """
    Revoke a specific session.

    Errors:
    - 403 if session does not belong to user
    """
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
    """
    Retrieve recent audit logs (admin only).

    Includes security and authentication events.
    """
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(100).all()

    return logs

@router.post("/password-reset/request")
def request_password_reset(body: ResetRequest, service: AuthService = Depends(get_auth_service),):
    """
    Request password reset.

    Sends reset link/token to registered email.
    """

    return service.request_password_reset(body.email)

@router.post("/password-reset/confirm")
def reset_password(body: ResetConfirm, service: AuthService = Depends(get_auth_service),):
    """
    Reset password using a valid reset token.

    Invalidates previous credentials.
    """

    return service.reset_password(
        token=body.token,
        new_password=body.new_password
    )

@router.post("/verify-email")
def verify_email(body: VerifyEmail, service: AuthService = Depends(get_auth_service),):
    """
    Verify user email using verification token.

    Activates user account.
    """

    return service.verify_email(
        token=body.token
    )

@router.post("/resend-verification")
def resend_verification(
    request: ResendVerificationRequest,
    service: AuthService = Depends(get_auth_service),
):
    """
    Resend email verification.

    Returns verification token (demo/testing mode).
    """
  
    result = service.resend_verification(request.email)    

    return {
        "message": "Verification email sent",
        "verification_token": result["verification_token"]
    }

@router.post("/request-otp", response_model=OTPResponse)
def request_otp(data: RequestOTPRequest, request: Request, background_tasks: BackgroundTasks,):
    """
    Send OTP to email.

    Notes:
    - Rate limited
    - OTP tied to device fingerprint and IP
    """

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

    background_tasks.add_task(email_service.send_otp_email, data.email, otp)

    return OTPResponse(message="OTP sent successfully", otp=otp)


@router.post("/login-otp", response_model=Union[LoginResponse, TwoFactorRequiredResponse])
def login_with_otp(
    data: LoginOTPRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service),
):
    """
    Login using email and OTP.

    Returns JWT tokens or triggers 2FA if enabled.

    Notes:
    - Device-aware authentication
    """

    
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


@router.get(
    "/oauth/google/login",
    summary="🔗 Google OAuth Login",
    description=get_google_login_description()
    )
def google_login(service: AuthService = Depends(get_auth_service)):
    """
    Start Google OAuth login.

    Redirects to Google with PKCE + state protection.
    """

    url = service.start_google_oauth(flow="login")

    return RedirectResponse(url)

@router.get("/oauth/google/callback")
def google_callback(
    request: Request,
    service: AuthService = Depends(get_auth_service),
):
    """
    Handle Google OAuth callback.

    Supports:
    - Login (create or fetch user)
    - Account linking

    Notes:
    - Validates state (CSRF protection)
    """
    
    code = request.query_params.get("code")
    state = request.query_params.get("state")
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
        
        ip_address = (
            request.headers.get("x-forwarded-for")
            or (request.client.host if request.client else None)
            or "127.0.0.1"
        )

        return service.handle_oauth_login(
            payload,
            request.headers.get("user-agent"),
            ip_address
        )

    # LINK FLOW
    if flow == "link":

        user_id = state_data["user_id"]

        return service.link_google_account(
            user_id,
            payload
        )

    raise HTTPException(400, "Invalid OAuth flow")

@router.get(
    "/oauth/google/link/start",
    summary="🔗 Start Google Account Linking",
    description="""
    ⚠️ This endpoint starts Google OAuth linking.

    👉 Steps:
    1. Click "Try it out"
    2. Execute request
    3. Copy `redirect_url` from response
    4. Open it in browser

    NOTE: OAuth cannot be completed inside Swagger UI.
    """
    )
def start_link_google(
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
):
    """
    Start Google account linking.

    Returns redirect URL for browser-based OAuth flow.
    """

    url = service.start_google_oauth(
        flow="link",
        user_id=str(current_user.id)
    )

    return {
        "redirect_url": url
    }

@router.get(
    "/oauth/github/login",
    summary="🔗 GitHub OAuth Login",
    description=get_github_login_description()
    )
def github_login(service: AuthService = Depends(get_auth_service)):
    """
    Start GitHub OAuth login.

    Redirects to GitHub authorization page.
    """

    url = service.start_github_oauth(flow="login")

    return RedirectResponse(url)

@router.get("/oauth/github/callback")
async def github_callback(
    request: Request,
    service: AuthService = Depends(get_auth_service),
):
    """
    Handle GitHub OAuth callback.

    Supports:
    - Login
    - Account linking

    Notes:
    - Uses provider abstraction layer
    """

    code = request.query_params.get("code")
    state = request.query_params.get("state")
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
        
        ip_address = (
            request.headers.get("x-forwarded-for")
            or (request.client.host if request.client else None)
            or "127.0.0.1"
        )

        return service.create_session(
            user=user,
            user_agent=request.headers.get("user-agent"),
            ip_address=ip_address
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

@router.get(
    "/oauth/github/link/start",
    summary="🔗 Start GitHub Account Linking",
    description="""
    ⚠️ This endpoint starts GitHub OAuth linking.

    👉 Steps:
    1. Click "Try it out"
    2. Execute request
    3. Copy `redirect_url` from response
    4. Open it in browser

    NOTE: OAuth cannot be completed inside Swagger UI.
    """
    )
def github_link_start(
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
):
    """
    Start GitHub account linking.

    Returns redirect URL for OAuth flow.
    """

    url = service.start_github_oauth(
        flow="link",
        user_id=str(current_user.id)
    )

    return {
        "redirect_url": url
    }


@router.post("/magic-link")
def request_magic_link(
    email: str,
    request: Request,
    service: AuthService = Depends(get_auth_service)
):
    """
    Send magic login link to email.

    Enables passwordless authentication.
    """

    ip = (
        request.headers.get("x-forwarded-for")
        or (request.client.host if request.client else None)
        or "127.0.0.1"
    )
    
    return service.request_magic_link(
        email,
        request.headers.get("user-agent"),
        ip
    )


@router.get("/magic-login")
def magic_login(
    token: str,
    request: Request,
    service: AuthService = Depends(get_auth_service)
):
    """
    Login using magic link token.

    Creates authenticated session.
    """
    ip = (
        request.headers.get("x-forwarded-for")
        or (request.client.host if request.client else None)
        or "127.0.0.1"
    )
    
    return service.login_with_magic_link(
        token,
        request.headers.get("user-agent"),
        ip
    )


@router.get("/approve-login")
def approve_login(
    request_id: str,
    request: Request,
    service: AuthService = Depends(get_auth_service)
):
    """
    Approve login request.

    Used for secure login confirmation (e.g., email approval flow).
    """
    ip = (
        request.headers.get("x-forwarded-for")
        or (request.client.host if request.client else None)
        or "127.0.0.1"
    )

    return service.approve_login(
        request_id,
        request.headers.get("user-agent"),
        ip
    )


@router.post("/request-phone-otp")
def request_phone_otp(data: RequestPhoneOTPRequest, request: Request):
    """
    Send OTP to phone number.

    Notes:
    - Rate limited
    - Delivered via SMS provider
    """

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
    """
    Login using phone OTP.

    Notes:
    - Auto-creates user if not registered
    - Supports 2FA if enabled
    """

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
    """
    Setup 2FA using TOTP.

    Returns secret and QR code for authenticator apps.
    """

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
    """
    Verify and enable 2FA.

    Returns recovery codes on success.
    """

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
    """
    Complete login using 2FA code.

    Requires valid MFA challenge.

    Notes:
    - Rate limited attempts
    """

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
    """
    Generate recovery codes for 2FA.

    Invalidates existing codes.
    """

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
    """
    Login using recovery code.

    Fallback when authenticator is unavailable.
    """

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
    """
    Regenerate recovery codes.

    Deletes old codes and issues new ones.
    """
    service.recovery_code_repo.delete_by_user(current_user.id)

    codes = recovery_code_service.generate_codes(current_user.id)

    return {"recovery_codes": codes}