import uuid
from datetime import datetime, timedelta, UTC
import pytest
from jose import jwt, JWTError, ExpiredSignatureError
from fastapi import HTTPException

from app.security.magic_link_jwt import create_magic_link_token, verify_magic_link_token
from app.core.config import settings


def test_create_magic_link_token_creates_payload_and_encodes():
    user_id = uuid.uuid4()
    email = "test@example.com"
    fingerprint = "fp123"
    ip = "127.0.0.1"

    token = create_magic_link_token(user_id, email, fingerprint, ip)

    # Decode to verify payload
    payload = jwt.decode(token, settings.JWT_PUBLIC_KEY, algorithms=[settings.JWT_ALGORITHM])

    assert payload["sub"] == str(user_id)
    assert payload["email"] == email
    assert payload["type"] == "magic_login"
    assert "jti" in payload
    assert payload["fingerprint"] == fingerprint
    assert payload["ip"] == ip
    assert "exp" in payload


def test_verify_magic_link_token_success():
    user_id = uuid.uuid4()
    email = "test@example.com"
    fingerprint = "fp123"
    ip = "127.0.0.1"

    token = create_magic_link_token(user_id, email, fingerprint, ip)
    payload = verify_magic_link_token(token)

    assert payload["sub"] == str(user_id)
    assert payload["email"] == email
    assert payload["type"] == "magic_login"
    assert payload["fingerprint"] == fingerprint
    assert payload["ip"] == ip


def test_verify_magic_link_token_expired():
    # Create a token with past expiration
    payload = {
        "sub": str(uuid.uuid4()),
        "email": "test@example.com",
        "type": "magic_login",
        "jti": str(uuid.uuid4()),
        "fingerprint": "fp123",
        "ip": "127.0.0.1",
        "exp": datetime.now(UTC) - timedelta(minutes=1)
    }
    token = jwt.encode(payload, settings.JWT_PRIVATE_KEY, algorithm=settings.JWT_ALGORITHM)

    with pytest.raises(HTTPException) as exc:
        verify_magic_link_token(token)
    assert exc.value.status_code == 400
    assert "expired" in str(exc.value.detail).lower()


def test_verify_magic_link_token_invalid():
    with pytest.raises(HTTPException) as exc:
        verify_magic_link_token("invalid.token.here")
    assert exc.value.status_code == 400
    assert "invalid" in str(exc.value.detail).lower()


def test_verify_magic_link_token_wrong_type():
    # Create a token with wrong type
    payload = {
        "sub": str(uuid.uuid4()),
        "email": "test@example.com",
        "type": "wrong_type",
        "jti": str(uuid.uuid4()),
        "fingerprint": "fp123",
        "ip": "127.0.0.1",
        "exp": datetime.now(UTC) + timedelta(minutes=10)
    }
    token = jwt.encode(payload, settings.JWT_PRIVATE_KEY, algorithm=settings.JWT_ALGORITHM)

    with pytest.raises(HTTPException) as exc:
        verify_magic_link_token(token)
    assert exc.value.status_code == 400
    assert "type" in str(exc.value.detail).lower()