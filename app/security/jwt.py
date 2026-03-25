import uuid
from datetime import datetime, timedelta, timezone, UTC
from jose import jwt, JWTError, ExpiredSignatureError
from fastapi import HTTPException, status
from app.core.config import settings
from app.security.token_blacklist import is_token_blacklisted
from app.repositories.user_repository import UserRepository
from app.core.database import SessionLocal

def create_access_token(data: dict, token_version: int):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    
    jti = str(uuid.uuid4())
    
    to_encode.update({
        "exp": expire,
        "jti": jti,
        "ver": token_version,
        })
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_PRIVATE_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return encoded_jwt

def verify_access_token(token: str):
    try:
        payload = jwt.decode(
            token,
            settings.JWT_PUBLIC_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        
        user_id = payload.get("sub")
        jti = payload.get("jti")
        token_version = payload.get("ver")
        
        if not user_id or jti is None or token_version is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 🔹 Blacklist check
        if is_token_blacklisted(jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return payload

    except ExpiredSignatureError as exc:
        # Token has expired
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    except JWTError as exc:
        # Token is invalid (tampered, wrong key, wrong algorithm, etc.)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

# def decode_access_token(token: str):
#     try:
#         return jwt.decode(
#             token,
#             settings.JWT_PUBLIC_KEY,
#             algorithms=[settings.JWT_ALGORITHM],
#         )
#     except ExpiredSignatureError:
#         raise HTTPException(...)

def decode_access_token(token: str):

    try:
        payload = jwt.decode(
            token,
            settings.JWT_PUBLIC_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        return payload

    except JWTError:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )