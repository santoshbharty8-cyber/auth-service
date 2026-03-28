# 🔐 Authentication Flow Diagrams — Auth Service

## 🧑‍💻 1. Password Login Flow
```text
Client
  │
  ▼
POST /login
  │
  ▼
AuthService.login()
  │
  ├── user_repo.find_by_email()
  │
  ├── Validate:
  │     - User exists
  │     - Email verified
  │     - Not locked
  │
  ├── authenticate("password")
  │
  ├── ❌ If invalid:
  │       - Increment failed_attempts
  │       - Lock account if needed
  │
  ├── ✅ If valid:
  │       - Reset attempts
  │
  ├── require_2fa(user)?
  │       │
  │       ├── YES → create MFA challenge (Redis)
  │       │         → return mfa_token
  │       │
  │       └── NO
  │
  ▼
create_session()
  │
  ├── create JWT access token
  ├── generate refresh token
  ├── store session in DB
  ├── audit log
  │
  ▼
Return tokens
```

## 🔄 2. Refresh Token Flow (Rotation-Based)
```text
Client
  │
  ▼
POST /refresh
  │
  ▼
AuthService.refresh()
  │
  ├── hash(refresh_token)
  ├── session_repo.find_by_hash()
  │
  ├── ❌ Not found:
  │       → possible reuse attack
  │       → reject
  │
  ├── ✅ Found:
  │       - Generate new refresh token
  │       - Update session (rotation)
  │       - Update last_active
  │
  ├── create new access token
  │
  ▼
Return new tokens
```

## 🚪 3. Logout Flow (Secure)
```text
Client
  │
  ▼
POST /logout
  │
  ▼
AuthService.logout()
  │
  ├── hash(refresh_token)
  ├── session_repo.find_by_hash()
  │
  ├── revoke session (DB)
  │
  ├── decode access token
  │
  ├── extract jti
  │
  ├── store jti in Redis blacklist (TTL)
  │
  ▼
Logout success
```

## 🚫 4. Force Logout All Devices
```text
Client
  │
  ▼
POST /force-logout-all
  │
  ▼
AuthService.force_logout_all()
  │
  ├── user.token_version += 1
  │
  ├── revoke all sessions (DB)
  │
  ▼
All tokens invalidated globally
```

## 📲 5. OTP Login Flow

### Step 1: Request OTP
```text
Client
  │
  ▼
POST /request-otp
  │
  ▼
OTPService.generate_otp()
  │
  ├── Rate limit check (Redis)
  │
  ├── Generate OTP
  ├── Hash OTP
  │
  ├── Store in Redis:
  │     - otp_hash
  │     - fingerprint
  │     - IP
  │
  ▼
OTP sent
```

### Step 2: Verify OTP
```text
Client
  │
  ▼
POST /login-otp
  │
  ▼
OTPService.verify_otp()
  │
  ├── Validate:
  │     - OTP hash
  │     - fingerprint match
  │     - attempts
  │
  ├── ❌ Invalid:
  │       → increment attempts
  │
  ├── ✅ Valid:
  │       → delete OTP
  │
  ▼
AuthService.create_session()
```

## 🔐 6. MFA (2FA) Flow

### Step 1: Challenge Creation
```text
Login success
  │
  ▼
require_2fa(user)
  │
  ▼
MFAChallengeService.create_challenge()
  │
  ├── Generate token
  ├── Store in Redis (TTL)
  ├── Store attempts counter
  │
  ▼
Return mfa_token
```

### Step 2: Verify TOTP
```text
Client
  │
  ▼
POST /2fa/login
  │
  ▼
MFAChallengeService.verify_challenge()
  │
  ├── Validate token
  ├── Check attempts
  │
  ▼
TOTPService.verify()
  │
  ├── ❌ Invalid:
  │       → increment attempts
  │
  ├── ✅ Valid:
  │       → delete challenge
  │
  ▼
create_session()
```

### Step 3: Recovery Code Login
```text
Client
  │
  ▼
POST /2fa/recovery
  │
  ▼
verify MFA challenge
  │
  ▼
RecoveryCodeService.verify_code()
  │
  ├── Check hash
  ├── Check unused
  │
  ▼
create_session()
```

## 🌐 7. OAuth Login Flow (Google/GitHub)
```text
Client
  │
  ▼
GET /oauth/google/login
  │
  ▼
AuthService.start_google_oauth()
  │
  ├── Generate state + PKCE
  ├── Store in Redis
  │
  ▼
Redirect to Google
  │
  ▼
Callback /oauth/google/callback
  │
  ▼
Validate state (Redis)
  │
  ▼
Exchange code → token
  │
  ▼
Fetch user profile
  │
  ▼
handle_oauth_login()
  │
  ├── Account exists?
  │       ├── YES → login
  │       └── NO → require linking
  │
  ▼
create_session()
```

## 🔗 8. Magic Link Login Flow
```text
Client
  │
  ▼
POST /magic-link
  │
  ▼
AuthService.request_magic_link()
  │
  ├── Generate JWT token
  │     - user_id
  │     - fingerprint
  │     - IP
  │
  ▼
Send login link

Click Magic Link
Client clicks link
  │
  ▼
GET /magic-login
  │
  ▼
verify_magic_link_token()
  │
  ├── Replay protection (Redis)
  │
  ├── Validate:
  │     - fingerprint match
  │     - IP match
  │
  ├── Trusted device?
  │       ├── YES → login
  │       └── NO → approval required
```

## 🔒 9. Suspicious Login Approval Flow
```text
Suspicious login detected
  │
  ▼
Store request in Redis
  │
  ▼
Send approval link
  │
  ▼
User clicks approve
  │
  ▼
GET /approve-login
  │
  ▼
Retrieve request from Redis
  │
  ▼
Save device (trusted)
  │
  ▼
create_session()
```

## 🛡️ 10. Rate Limiting Flow
```text
Client request
  │
  ▼
Redis counter increment
  │
  ├── If limit exceeded:
  │       → reject (429)
  │
  └── Else:
          → allow
```

## 🎯 Final Summary
This system supports:
- Multi-auth (password, OTP, OAuth, magic link)
- Strong MFA (TOTP + recovery)
- Session-based security
- Device-aware login
- Attack protection (rate limit, lockout, replay)

---  

# 🔑 11. WebAuthn (Passkey / Biometric Login) Flow

WebAuthn enables passwordless + phishing-resistant authentication using devices like:
- Fingerprint
- Face ID
- Security keys

## 🧾 11.1 Registration (Credential Creation)
```text
Client
  │
  ▼
GET /webauthn/register/start
  │
  ▼
WebAuthnService.generate_registration_options()
  │
  ├── Generate challenge
  ├── Store challenge in Redis
  │
  ▼
Return options to client
  │
  ▼
Browser → navigator.credentials.create()
  │
  ▼
POST /webauthn/register/finish
  │
  ▼
WebAuthnService.verify_registration()
  │
  ├── Validate challenge
  ├── Verify attestation
  │
  ▼
Store credential in DB
(WebAuthnCredential)
```

👉 Stored model

## 🔐 11.2 Authentication (Login)
```text
Client
  │
  ▼
GET /webauthn/login/start
  │
  ▼
WebAuthnService.generate_authentication_options()
  │
  ├── Generate challenge
  ├── Store in Redis
  │
  ▼
Return options
  │
  ▼
Browser → navigator.credentials.get()
  │
  ▼
POST /webauthn/login/finish
  │
  ▼
WebAuthnService.verify_authentication()
  │
  ├── Validate challenge
  ├── Verify signature
  ├── Check sign_count (replay protection)
  │
  ▼
Fetch user via credential_id
  │
  ▼
AuthService.create_session()
```

## 🔐 11.3 Credential Storage
WebAuthnCredential:
- credential_id (unique)
- public_key
- sign_count
- user_id

👉 Used for:
- Verifying future logins
- Preventing replay attacks

## 🛡️ Security Features
- ✔ Challenge-based authentication
  - Prevents replay attacks
- ✔ Public-key cryptography
  - No password stored
- ✔ Sign counter
  - Detect cloned devices
- ✔ Origin binding
  - Prevents phishing

## ⚡ Where It Fits in Your System
WebAuthn integrates with your existing flows:

```text
Login request
  │
  ├── Password
  ├── OTP
  ├── OAuth
  ├── Magic Link
  └── WebAuthn  ← NEW
```

--- 


# 📧 Registration & Email Verification Flow

## 🧑‍💻 1. User Registration Flow

## 🔁 End-to-End Flow
```text
Client
  │
  ▼
POST /register
  │
  ▼
AuthService.register()
  │
  ├── user_repo.exists_by_email()
  │
  ├── ❌ If exists:
  │       → return error
  │
  ├── ✅ Create user:
  │       - email
  │       - password_hash
  │       - status = PENDING
  │
  ├── Generate verification token (UUID)
  │
  ├── Hash token
  │
  ├── Store in DB:
  │       EmailVerificationToken
  │       - user_id
  │       - token_hash
  │       - expires_at (24h)
  │
  ├── Build verification link:
  │       /verify-email?token=...
  │
  ├── (Send email) ← currently print/log
  │
  ├── Audit log → REGISTER SUCCESS
  │
  ▼
Return:
- user info
- verification_token
```

👉 Implementation reference:

## 🗄️ Database Changes

### 👤 User Table
- status = "PENDING"

👉 User cannot login until verified

### 📧 EmailVerificationToken Table
- user_id
- token_hash
- expires_at

👉 Token stored as hash (secure design)

## 🔐 2. Email Verification Flow

## 🔁 End-to-End Flow
```text
Client clicks email link
  │
  ▼
POST /verify-email
  │
  ▼
AuthService.verify_email()
  │
  ├── Hash incoming token
  │
  ├── email_verification_repo.find_by_hash()
  │
  ├── ❌ If not found:
  │       → invalid token
  │
  ├── Check expiry
  │
  ├── ❌ If expired:
  │       → reject
  │
  ├── Fetch user
  │
  ├── Update user:
  │       status = ACTIVE
  │
  ├── Delete verification token
  │
  ▼
Return success
```

👉 Implementation reference:

## 🔁 3. Resend Verification Flow
```text
Client
  │
  ▼
POST /resend-verification
  │
  ▼
AuthService.resend_verification()
  │
  ├── find user
  │
  ├── ❌ If not found:
  │       → error
  │
  ├── ❌ If already ACTIVE:
  │       → reject
  │
  ├── Delete old tokens
  │
  ├── Generate new token
  │
  ├── Store hashed token
  │
  ├── Send email
  │
  ├── Audit log
  │
  ▼
Return new token
```

## 🚫 4. Login Restriction (Critical Security)
```text
POST /login
  │
  ▼
AuthService.login()
  │
  ├── Check user.status
  │
  ├── ❌ If not ACTIVE:
  │       → reject login
  │       → "Email not verified"
  │
  ▼
Proceed only if verified
```

👉 Implementation reference:

## 🛡️ Security Design
- ✔ Token Hashing  
  Raw token never stored in DB  
  Prevents DB leakage attacks
- ✔ Expiration (24 hours)  
  Limits token misuse window
- ✔ One-Time Use  
  Token deleted after verification
- ✔ Login Blocking  
  Unverified users cannot login
- ✔ Resend Flow Protection  
  Old tokens deleted  
  Prevents multiple valid tokens

## ⚡ Edge Cases Handled

Scenario | Behavior
--- | ---
Email already exists | Reject
Token expired | Reject
Token invalid | Reject
Already verified | Reject resend
Multiple requests | Old tokens removed

## 🧠 Sequence Summary
```text
Register → PENDING user
        → token generated
        → email sent

Verify → token validated
       → user activated
       → token deleted

Login → allowed only if ACTIVE
```


--- 

# 🔐 Advanced Authentication Flows

## 🔁 1. Password Reset Flow

### 📩 Step 1: Request Reset
```text
Client
  │
  ▼
POST /password-reset/request
  │
  ▼
AuthService.request_password_reset()
  │
  ├── user_repo.find_by_email()
  │
  ├── ❌ If not found:
  │       → return generic message (no user leak)
  │
  ├── Generate reset token (UUID)
  │
  ├── Hash token
  │
  ├── Store in DB:
  │       PasswordResetToken
  │       - user_id
  │       - token_hash
  │       - expires_at (30 min)
  │
  ├── Send reset link
  │
  ▼
Return success message
```

👉 Ref:

### 🔑 Step 2: Reset Password
```text
Client
  │
  ▼
POST /password-reset/confirm
  │
  ▼
AuthService.reset_password()
  │
  ├── Hash token
  │
  ├── find token in DB
  │
  ├── ❌ If invalid/expired:
  │       → reject
  │
  ├── Fetch user
  │
  ├── Update:
  │       - password_hash
  │       - token_version += 1
  │
  ├── Revoke all sessions
  │
  ├── Delete reset token
  │
  ▼
Password updated
```

## 📧 2. Login with Email OTP Flow

### Step 1: Request OTP
```text
Client
  │
  ▼
POST /request-otp
  │
  ▼
OTPService.generate_otp()
  │
  ├── Rate limit (Redis)
  │
  ├── Generate OTP
  ├── Hash OTP
  │
  ├── Store in Redis:
  │       - otp_hash
  │       - fingerprint
  │       - IP
  │
  ▼
Send OTP (email)
```

👉 Ref:

### Step 2: Login with OTP
```text
Client
  │
  ▼
POST /login-otp
  │
  ▼
AuthService.authenticate("otp")
  │
  ▼
OTPService.verify_otp()
  │
  ├── Validate:
  │       - OTP hash
  │       - fingerprint
  │       - attempts
  │
  ├── ❌ Invalid:
  │       → increment attempts
  │
  ├── ✅ Valid:
  │       → delete OTP
  │
  ▼
require_2fa(user)?
  │
  ├── YES → return mfa_token
  │
  └── NO
        ▼
create_session()
```

## 📱 3. Login with Phone OTP Flow

### Step 1: Request Phone OTP
```text
Client
  │
  ▼
POST /request-phone-otp
  │
  ▼
OTPService.generate_otp()
  │
  ├── Rate limit
  │
  ├── Generate OTP
  │
  ▼
SMSService.send_otp()
```

👉 Ref:

### Step 2: Login via Phone OTP
```text
Client
  │
  ▼
POST /login-phone-otp
  │
  ▼
OTPService.verify_otp()
  │
  ├── ❌ Invalid → reject
  │
  ├── ✅ Valid:
  │
  ▼
user_repo.find_by_phone()
  │
  ├── If not exists:
  │       → create phone user
  │
  ▼
require_2fa(user)?
  │
  ├── YES → return mfa_token
  │
  └── NO
        ▼
create_session()
```

## 🐙 4. GitHub OAuth Login Flow

### Step 1: Redirect to GitHub
```text
Client
  │
  ▼
GET /oauth/github/login
  │
  ▼
AuthService.start_github_oauth()
  │
  ├── Generate state + PKCE
  ├── Store in Redis
  │
  ▼
Redirect to GitHub
```

### Step 2: Callback
```text
GitHub → callback
  │
  ▼
GET /oauth/github/callback
  │
  ▼
Validate state (Redis)
  │
  ▼
Exchange code → token
  │
  ▼
Fetch profile + email
  │
  ▼
AuthService.handle_github_oauth_login()
  │
  ├── Existing OAuth account?
  │       ├── YES → login
  │       └── NO
  │
  ├── Existing user with email?
  │       ├── YES → ask to link
  │       └── NO → create new user
  │
  ▼
require_2fa(user)?
  │
  ├── YES → return mfa_token
  │
  └── NO
        ▼
create_session()
```

👉 Ref:

## 🔐 5. 2FA Login with Recovery Code
```text
Client
  │
  ▼
POST /2fa/recovery
  │
  ▼
MFAChallengeService.verify_challenge()
  │
  ├── ❌ Invalid/expired → reject
  │
  ▼
RecoveryCodeService.verify_code()
  │
  ├── Check:
  │       - hash match
  │       - unused
  │
  ├── ❌ Invalid:
  │       → increment attempts
  │
  ├── ✅ Valid:
  │       → mark used
  │
  ▼
Delete MFA challenge
  │
  ▼
create_session()
```

👉 Ref:

## 🛡️ Security Highlights
- ✔ Password Reset
  - Token hashed
  - Expiry enforced
  - All sessions revoked
- ✔ OTP
  - Stored in Redis
  - Fingerprint + IP binding
  - Attempt limits
- ✔ OAuth
  - PKCE + state validation
  - Prevents CSRF
- ✔ Recovery Codes
  - One-time use
  - Stored hashed
- ✔ MFA
  - Challenge-based (Redis)
  - Attempt tracking

## 🎯 Final Summary

Flow | Security Level
--- | ---
Password Reset | 🔥🔥🔥
Email OTP | 🔥🔥
Phone OTP | 🔥🔥
GitHub OAuth | 🔥🔥🔥
Recovery Code Login | 🔥🔥🔥


----

# 🛠️ Admin & RBAC Flows — Auth Service

## 📌 Overview
The admin system provides:
- Role management
- Permission management
- User-role assignment
- Access control (RBAC enforcement)

👉 Built using:
- Role
- Permission
- RBACService

## 🧱 Core Models

### 🧑‍💼 Role
Role:
- id
- name (ADMIN, USER, etc.)

### 🔑 Permission
Permission:
- id
- name (CREATE_USER, DELETE_USER, etc.)

### 🔗 Role-Permission Mapping
Role ↔ Permission (Many-to-Many)

### 👤 User-Role Mapping
User ↔ Role (Many-to-Many)

👉 Enables flexible access control

## 🔐 1. RBAC Enforcement Flow
```text
Client request
  │
  ▼
API endpoint (protected)
  │
  ▼
RBACService.user_has_permission(user, permission)
  │
  ├── Loop:
  │       for role in user.roles
  │           for permission in role.permissions
  │
  ├── Match found?
  │       ├── YES → allow
  │       └── NO → reject (403)
```

👉 Ref:

## 🛠️ 2. Create Role Flow
```text
Admin Client
  │
  ▼
POST /admin/roles
  │
  ▼
RoleRepository.create()
  │
  ├── Validate uniqueness
  │
  ▼
Store role in DB
```

## 🔑 3. Create Permission Flow
```text
Admin Client
  │
  ▼
POST /admin/permissions
  │
  ▼
PermissionRepository.create()
  │
  ▼
Store permission
```

## 🔗 4. Assign Permission to Role
```text
Admin Client
  │
  ▼
POST /admin/roles/{role_id}/permissions
  │
  ▼
Find role
  │
  ▼
Find permission
  │
  ▼
Attach permission to role
  │
  ▼
Save role
```

## 👤 5. Assign Role to User
```text
Admin Client
  │
  ▼
POST /admin/users/{user_id}/roles
  │
  ▼
Find user
  │
  ▼
Find role
  │
  ▼
Attach role to user
  │
  ▼
Save user
```

## 📋 6. List Roles & Permissions
```text
GET /admin/roles
GET /admin/permissions
  │
  ▼
Fetch from DB
  │
  ▼
Return list
```

## 🚫 7. Protected Admin Endpoint Flow
```text
Client
  │
  ▼
Request /admin/*
  │
  ▼
JWT Authentication
  │
  ▼
Extract user
  │
  ▼
RBACService check
  │
  ├── ❌ No permission:
  │       → 403 Forbidden
  │
  ├── ✅ Allowed:
  │       → execute API
```

## 🛡️ Security Design
- ✔ Permission-Based Access
  - Fine-grained control (not just roles)
- ✔ Role Abstraction
  - Roles group permissions
  - Easy scalability
- ✔ DB-Level Relationships
  - Many-to-many mapping
  - Flexible system
- ✔ Separation of Concerns
  - RBAC logic isolated in service

## ⚡ Example
Scenario:  
User tries to delete another user  
Permission required: `DELETE_USER`

User roles:
- ADMIN → has `DELETE_USER` → ✅ allowed
- USER → no permission → ❌ denied

## 🧠 Design Pattern Used
- ✔ RBAC (Role-Based Access Control)

Structure:
```text
User → Roles → Permissions
```

## 🚀 Future Improvements (Advanced)
- ABAC (Attribute-Based Access Control)
- Policy engine (like OPA)
- Dynamic permissions (time/location-based)
- Admin audit logs (who changed what)


--------

