from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse
from app.core.config import settings
from app.security.dependencies import get_current_user
from app.dependencies.services import get_webauthn_service
from app.dependencies.auth_dependencies import get_auth_service
from app.schemas.auth_schema import LoginStartRequest
from app.repositories.user_repository import UserRepository
from app.core.database import get_db

router = APIRouter(prefix="/webauthn", tags=["WebAuthn"])



@router.get("/register/start")
def start_registration(
    current_user=Depends(get_current_user),
    service=Depends(get_webauthn_service)
):
    """
    Start WebAuthn (passkey) registration.

    Generates a challenge and returns publicKey options for client-side credential creation.

    Requires authenticated user.

    Notes:
    - Challenge is stored in Redis (expires in 5 minutes)
    - Must be completed via `/webauthn/register/finish`
    """

    try:
        return service.start_registration(current_user)

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@router.post("/register/finish")
def finish_registration(
    credential: dict,
    current_user=Depends(get_current_user),
    service=Depends(get_webauthn_service)
):
    """
    Complete WebAuthn registration.

    Verifies credential response from client and stores passkey.

    Requires authenticated user.

    Notes:
    - Validates challenge from Redis
    - Stores credential (public key, sign count)
    - Fails if registration session expired
    """
    
    try:
        return service.finish_registration(current_user, credential)
    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@router.post("/login/start")
def start_login(
    payload: LoginStartRequest,
    service=Depends(get_webauthn_service),
    db: Session = Depends(get_db)
):
    """
    Start WebAuthn login.

    ⚠️ Requires browser with WebAuthn support (Passkeys).

    Flow:
    1. Call this endpoint
    2. Use response in frontend (navigator.credentials.get)
    3. Send result to `/webauthn/login/finish`
    
    Start WebAuthn login.

    Generates authentication challenge for registered passkeys.

    Notes:
    - Requires user email
    - Fails if no passkeys registered
    - Challenge stored in Redis (expires in 5 minutes)
    """
    try:
        user_repo = UserRepository(db)
        user = user_repo.find_by_email(payload.email)
        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
        return service.start_login(user)
    
    except HTTPException:
        raise

    except Exception as e:
        
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@router.post("/login/finish")
def finish_login(
    credential: dict,
    request: Request,
    webauthn_service=Depends(get_webauthn_service),
    auth_service=Depends(get_auth_service)
):
    """
    Complete WebAuthn login.

    Verifies passkey authentication and creates user session.

    Returns JWT session (access + refresh tokens).

    Notes:
    - Validates challenge and credential signature
    - Enforces replay protection using sign counter
    - Captures IP and User-Agent for session tracking

    Errors:
    - 401 if authentication fails
    - 400 for invalid WebAuthn response
    """
    try:
        user = webauthn_service.finish_login(credential)
        
        if not user:
            raise HTTPException(
                status_code=401,
                detail="Invalid passkey authentication"
            )               

        ip = (
            request.headers.get("x-forwarded-for")
            or (request.client.host if request.client else None)
            or "127.0.0.1"
        )
        
        return auth_service.create_session(
            user,
            user_agent=request.headers.get("user-agent"),
            ip_address=ip
        )
    except ValueError as e:
        # WebAuthn verification errors
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    except HTTPException:
        raise

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.get(
    "/demo", 
    response_class=HTMLResponse, 
    tags=["WebAuthn"],
    description=f"""         
    WebAuthn Live Demo

    Open in browser:

    {settings.BASE_URL}/webauthn/demo

    WebAuthn cannot be tested inside Swagger
    """
    )
def webauthn_demo():
    return """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Auth Demo (Password + 2FA + Passkey)</title>
</head>

<body>

<h2>🔐 Auth Demo</h2>

<h3>Step 1: Login</h3>
<input id="email" placeholder="Email" />
<input id="password" type="password" placeholder="Password" />
<button onclick="login()">Login</button>

<div id="otp-section" style="display:none;">
<h3>Step 2: Enter OTP</h3>
<input id="otp" placeholder="Enter 6-digit OTP" />
<button onclick="verifyOtp()">Verify OTP</button>
</div>

<h3>Step 3: Register Passkey</h3>
<button onclick="register()">Register Passkey</button>

<h3>Step 4: Login with Passkey</h3>
<button onclick="loginPasskey()">Login with Passkey</button>

<script>

// -----------------------------
// Base64URL → ArrayBuffer (FIXED)
// -----------------------------
function base64urlToBuffer(base64url){
    const padding = '='.repeat((4 - base64url.length % 4) % 4)

    const base64 = (base64url + padding)
        .replace(/-/g,"+")
        .replace(/_/g,"/")

    const binary = atob(base64)

    const bytes = new Uint8Array(binary.length)

    for(let i=0;i<binary.length;i++){
        bytes[i] = binary.charCodeAt(i)
    }

    return bytes.buffer
}

// -----------------------------
// ArrayBuffer → Base64URL
// -----------------------------
function bufferToBase64url(buffer){
    const bytes = new Uint8Array(buffer)
    let binary = ""

    for(let i=0;i<bytes.length;i++){
        binary += String.fromCharCode(bytes[i])
    }

    return btoa(binary)
        .replace(/\\+/g,"-")
        .replace(/\\//g,"_")
        .replace(/=+$/,"")
}

// -----------------------------
// LOGIN (Password)
// -----------------------------
async function login(){

    try{
        const email = document.getElementById("email").value
        const password = document.getElementById("password").value

        const res = await fetch("/auth/login", {
            method:"POST",
            headers: {"Content-Type":"application/json"},
            body: JSON.stringify({email, password})
        })

        const data = await res.json()

        console.log("Login response:", data)

        if(data.require_2fa){
            localStorage.setItem("mfa_token", data.mfa_token)
            document.getElementById("otp-section").style.display = "block"
            alert("2FA required")
        }else{
            localStorage.setItem("token", data.access_token)
            alert("Login success")
        }

    }catch(err){
        console.error(err)
        alert("Login failed")
    }
}

// -----------------------------
// VERIFY OTP (2FA)
// -----------------------------
async function verifyOtp(){

    try{
        const code = document.getElementById("otp").value
        const mfa_token = localStorage.getItem("mfa_token")

        const res = await fetch("/auth/2fa/login", {
            method:"POST",
            headers: {"Content-Type":"application/json"},
            body: JSON.stringify({mfa_token, code})
        })

        const data = await res.json()

        localStorage.setItem("token", data.access_token)

        alert("2FA Login success")

    }catch(err){
        console.error(err)
        alert("2FA failed")
    }
}

// -----------------------------
// REGISTER PASSKEY
// -----------------------------
async function register(){

    try{

        window.focus()

        if(!document.hasFocus()){
            alert("Click on page first")
            return
        }

        const token = localStorage.getItem("token")

        const res = await fetch("/webauthn/register/start", {
            headers: {
                "Authorization": "Bearer " + token
            }
        })

        const options = await res.json()

        console.log("Register options:", options)

        options.publicKey.challenge =
            base64urlToBuffer(options.publicKey.challenge)

        options.publicKey.user.id =
            base64urlToBuffer(options.publicKey.user.id)

        options.publicKey.timeout = 60000
        options.publicKey.attestation = "none"

        const cred = await navigator.credentials.create({
            publicKey: options.publicKey
        })

        console.log("Credential created:", cred)

        const payload = {
            id: cred.id,
            rawId: bufferToBase64url(cred.rawId),
            type: cred.type,
            response: {
                clientDataJSON: bufferToBase64url(
                    cred.response.clientDataJSON
                ),
                attestationObject: bufferToBase64url(
                    cred.response.attestationObject
                )
            }
        }

        const finish = await fetch("/webauthn/register/finish", {
            method:"POST",
            headers:{
                "Content-Type":"application/json",
                "Authorization":"Bearer " + token
            },
            body: JSON.stringify(payload)
        })

        const result = await finish.json()

        console.log("Register result:", result)

        alert("Passkey registered!")

    }catch(err){
        console.error("Register error:", err)
        alert("Registration failed: " + err.message)
    }
}

// -----------------------------
// LOGIN WITH PASSKEY
// -----------------------------
async function loginPasskey(){

    try{

        const email = document.getElementById("email").value

        const res = await fetch("/webauthn/login/start", {
            method:"POST",
            headers: {"Content-Type":"application/json"},
            body: JSON.stringify({email})
        })

        const options = await res.json()

        console.log("Login options:", options)

        options.publicKey.challenge =
            base64urlToBuffer(options.publicKey.challenge)

        options.publicKey.allowCredentials.forEach(c=>{
            c.id = base64urlToBuffer(c.id)
        })

        const cred = await navigator.credentials.get({
            publicKey: options.publicKey
        })

        const payload = {
            id: cred.id,
            rawId: bufferToBase64url(cred.rawId),
            response: {
                clientDataJSON: bufferToBase64url(
                    cred.response.clientDataJSON
                ),
                authenticatorData: bufferToBase64url(
                    cred.response.authenticatorData
                ),
                signature: bufferToBase64url(
                    cred.response.signature
                )
            }
        }

        const result = await fetch("/webauthn/login/finish", {
            method:"POST",
            headers: {"Content-Type":"application/json"},
            body: JSON.stringify(payload)
        }).then(r => r.json())

        console.log("Login result:", result)

        alert("Passkey login success")

    }catch(err){
        console.error(err)
        alert("Passkey login failed")
    }
}

</script>

</body>
</html>
"""