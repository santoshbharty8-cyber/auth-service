from jose import jwt, JWTError, ExpiredSignatureError
from datetime import datetime, timedelta, UTC
import uuid

from fastapi import HTTPException
from app.core.config import settings


def create_magic_link_token(user_id, email, fingerprint, ip):

    payload = {
        "sub": str(user_id),
        "email": email,
        "type": "magic_login",
        "jti": str(uuid.uuid4()),
        "fingerprint": fingerprint,
        "ip": ip,
        "exp": datetime.now(UTC) + timedelta(minutes=10)
    }

    return jwt.encode(
        payload,
        settings.JWT_PRIVATE_KEY,
        algorithm=settings.JWT_ALGORITHM
    )


def verify_magic_link_token(token: str):

    try:
        payload = jwt.decode(
            token,
            settings.JWT_PUBLIC_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )

    except ExpiredSignatureError:
        raise HTTPException(400, "Magic link expired")

    except JWTError:
        raise HTTPException(400, "Invalid magic link")

    if payload.get("type") != "magic_login":
        raise HTTPException(400, "Invalid token type")

    return payload