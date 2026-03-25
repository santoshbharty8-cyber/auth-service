from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import uuid

from app.core.database import get_db
from app.security.jwt import verify_access_token
from app.repositories.user_repository import UserRepository

security = HTTPBearer()


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):

    payload = verify_access_token(credentials.credentials)

    user_id = payload.get("sub")
    token_version = payload["ver"]
    request.state.user_id = user_id
    

    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    
    try:
        user_uuid = uuid.UUID(user_id)   # convert string → UUID
    except ValueError as exc:
        raise HTTPException(
            status_code=401,
            detail="Invalid user ID format",
        ) from exc


    user_repo = UserRepository(db)
    user = user_repo.find_by_id(user_uuid)

    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    if user.token_version != token_version:
        raise HTTPException(status_code=401, detail="Session invalidated")

    return user