# 🔬 Low-Level Design (LLD) — Auth Service

## 📌 Overview
This document describes the internal working, data models, and service interactions of the Auth Service.

**Architecture follows:**
- 👉 API → Service → Repository → DB
- 👉 Security + Redis → Cross-cutting concerns

## 🧱 1. Core Modules

### 1.1 API Layer (app/api)
Handles request/response.

**Example:**
```
POST /login 
→ auth_service.login()
```



👉 **Extracts:**
- IP address
- User agent

Then delegates to service


--- 

### 1.2 Service Layer (app/services)

**🔥 Central Class: AuthService**

**Responsible for:**
- Authentication
- Token lifecycle
- Session management
- OAuth handling
- Magic link
- 2FA orchestration

👉 **Entry methods:**
- `login()`
- `register()`
- `refresh()`
- `logout()`
- `create_session()`

--- 

### 1.3 Repository Layer
Encapsulates DB access:

**Example:**
``` 
user = user_repo.find_by_email(email)
session = session_repo.find_by_hash(token_hash)
``` 


👉 Ensures clean separation

--- 

## 🗄️ 2. Database Design (Entities)

### 👤 User
User:
- id (UUID)
- email
- password_hash
- status (ACTIVE / PENDING)
- failed_attempts
- locked_until
- token_version
- phone_number

👉 Used for:
- Authentication
- Account locking
- Global logout (token_version)

### 🔑 UserSession
UserSession:
- id
- user_id
- refresh_token_hash
- user_agent
- ip_address
- is_active
- last_active_at

👉 Supports:
- Multi-device login
- Session tracking
- Token rotation

### 🔄 RefreshToken (legacy support)
- Stores hashed refresh tokens

### 🔐 OAuthAccount
OAuthAccount:
- provider (google/github)
- provider_user_id
- email

👉 Maps external identity → internal user

### 🔐 TOTP (2FA)
TOTPCredential:
- user_id
- secret
- is_enabled

### 🔐 Recovery Codes
RecoveryCode:
- user_id
- code_hash
- used

### 📱 UserDevice
UserDevice:
- user_id
- fingerprint
- ip
- user_agent

👉 Used in:
- Magic link trust system

### 🧾 AuditLog
AuditLog:
- event_type
- event_status
- ip_address
- metadata

### 🔐 Token Tables
- PasswordResetToken
- EmailVerificationToken

--- 

## 🔁 3. Core Flows (Internal)

### 🔐 3.1 Login Flow (Password)
Step-by-step:
1. API receives request
2. AuthService.login()
3. user_repo.find_by_email()
4. Validate:
   - user exists
   - email verified
   - account not locked
5. authenticate("password")
6. On failure:
   → increment failed_attempts
   → lock account if threshold reached
7. On success:
   → reset attempts
8. Check 2FA:
   → if enabled → return MFA challenge
9. Else:
   → create_session()

### 🔄 3.2 Session Creation
create_session():

1. Generate access_token (JWT)
2. Generate refresh_token
3. Hash refresh token
4. Store in UserSession
5. Log audit event
6. Return tokens

### 🔁 3.3 Refresh Token Flow
1. Hash incoming refresh token
2. session_repo.find_by_hash()
3. If not found → reject
4. Generate new refresh token
5. Update session (rotation)
6. Generate new access token

👉 Protects against token reuse attacks

### 🚪 3.4 Logout Flow
1. Find session by refresh token
2. Revoke session
3. Decode access token
4. Extract jti
5. Store in Redis blacklist (TTL)

### 🚫 3.5 Force Logout All
1. Increment user.token_version
2. Revoke all sessions

👉 Invalidates ALL tokens instantly

### 📧 3.6 Email Verification
1. Generate UUID token
2. Hash token
3. Store in DB
4. Send link
5. Verify:
   → match hash
   → check expiry
   → activate user

### 🔁 3.7 Password Reset
1. Generate token
2. Store hashed token
3. On confirm:
   → validate token
   → update password
   → increment token_version
   → revoke sessions

### 📲 3.8 OTP Flow

Generate OTP
1. Generate 6-digit OTP
2. Hash OTP
3. Store in Redis:
   - otp
   - fingerprint
   - ip
4. Set expiry

Verify OTP
1. Fetch from Redis
2. Validate:
   - OTP hash
   - fingerprint
   - attempts
3. Delete OTP on success

### 🔐 3.9 MFA (2FA)

Challenge Creation
1. Generate token
2. Store in Redis (TTL)
3. Track attempts

Verify TOTP
1. Validate challenge token
2. Fetch user
3. Verify TOTP secret
4. On success:
   → delete challenge
   → create session

### 🔑 3.10 OAuth Flow
1. Generate state + PKCE
2. Store in Redis
3. Redirect to provider
4. Callback:
   → validate state
   → exchange code
   → fetch profile
5. If user exists:
   → login
6. Else:
   → require linking

### 🔗 3.11 Magic Link Flow
1. Generate JWT with:
   - user_id
   - fingerprint
   - ip
2. On click:
   → verify token
   → prevent replay (Redis)
3. Check:
   - fingerprint match
   - IP match
4. If trusted:
   → login
5. Else:
   → require approval

### 🔒 3.12 Login Approval Flow
1. Store request in Redis
2. User clicks approve link
3. Save device
4. Create session

--- 

## ⚙️ 4. Redis Key Design

Feature | Key
--- | ---
OTP | `otp:{identifier}`
OTP attempts | `otp_attempts:{identifier}`
MFA | `mfa_challenge:{token}`
Rate limit | `otp_rate:{identifier}`
Magic link replay | `magic:{jti}`

## 🛡️ 5. Security Internals

### Token Security
- Access token → JWT
- Refresh token → DB + hash
- Blacklist → Redis

### Device Security
- Fingerprint = hash(user_agent + IP)
- Used in:
  - OTP
  - Magic link

### Attack Protection
- Brute force → account lock
- OTP attempts limit
- MFA attempts limit
- Token reuse protection

## ⚡ 6. Key Design Patterns

- ✔ Repository Pattern
  - DB abstraction
- ✔ Strategy Pattern
  - Auth providers (password, OTP, OAuth)
- ✔ Token Rotation Pattern
  - Refresh token security
- ✔ Challenge-Response Pattern
  - MFA system

## 🚀 Summary

This LLD demonstrates:
- Strong separation of concerns
- Secure authentication design
- Multi-auth extensibility
- Production-grade token lifecycle

--- 