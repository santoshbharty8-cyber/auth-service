from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, Request, HTTPException
from app.security.dependencies import get_current_user
from app.dependencies.services import get_webauthn_service
from app.dependencies.auth_dependencies import get_auth_service
from app.schemas.auth_schema import LoginStartRequest
from app.repositories.webauthn_repository import WebAuthnRepository
from app.repositories.user_repository import UserRepository
from app.core.database import get_db

router = APIRouter(prefix="/webauthn", tags=["WebAuthn"])



@router.get("/register/start")
def start_registration(
    current_user=Depends(get_current_user),
    service=Depends(get_webauthn_service)
):

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