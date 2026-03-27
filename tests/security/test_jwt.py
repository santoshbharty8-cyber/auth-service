import uuid
from datetime import datetime, timedelta, timezone
import pytest
from jose import jwt, JWTError, ExpiredSignatureError
from fastapi import HTTPException

from app.security.jwt import create_access_token, verify_access_token, decode_access_token


def test_create_access_token_basic():
    """Test basic token creation"""
    data = {"sub": str(uuid.uuid4())}
    token_version = 1
    token = create_access_token(data, token_version)
    assert isinstance(token, str)
    assert len(token) > 0


def test_verify_access_token_valid():
    """Test verifying a valid token"""
    user_id = str(uuid.uuid4())
    data = {"sub": user_id}
    token_version = 1
    token = create_access_token(data, token_version)
    
    payload = verify_access_token(token)
    assert payload["sub"] == user_id
    assert "exp" in payload
    assert "jti" in payload
    assert payload["ver"] == token_version


def test_verify_access_token_blacklisted(monkeypatch):
    """Test verifying a blacklisted token - covers line 44"""
    from app.security import jwt
    monkeypatch.setattr(jwt, "is_token_blacklisted", lambda jti: True)
    
    user_id = str(uuid.uuid4())
    data = {"sub": user_id}
    token_version = 1
    token = create_access_token(data, token_version)
    
    with pytest.raises(HTTPException) as exc:
        verify_access_token(token)
    assert exc.value.status_code == 401
    assert "revoked" in exc.value.detail


def test_verify_access_token_expired(monkeypatch):
    """Test verifying an expired token"""
    from app.security import jwt
    monkeypatch.setattr(jwt, "jwt", type('MockJWT', (), {
        'decode': lambda *args, **kwargs: (_ for _ in ()).throw(ExpiredSignatureError())
    })())
    
    with pytest.raises(HTTPException) as exc:
        verify_access_token("expired_token")
    assert exc.value.status_code == 401
    assert "expired" in exc.value.detail


def test_verify_access_token_invalid_payload(monkeypatch):
    """Test verifying token with invalid payload"""
    from app.security import jwt
    monkeypatch.setattr(jwt, "jwt", type('MockJWT', (), {
        'decode': lambda *args, **kwargs: {"sub": None, "jti": None, "ver": None}
    })())
    
    with pytest.raises(HTTPException) as exc:
        verify_access_token("invalid_payload_token")
    assert exc.value.status_code == 401
    assert "Invalid token payload" in exc.value.detail


def test_decode_access_token_valid():
    """Test decoding a valid token"""
    user_id = str(uuid.uuid4())
    data = {"sub": user_id}
    token_version = 1
    token = create_access_token(data, token_version)
    
    payload = decode_access_token(token)
    assert payload["sub"] == user_id


def test_decode_access_token_invalid(monkeypatch):
    """Test decoding an invalid token - covers lines 97-99"""
    from app.security import jwt
    monkeypatch.setattr(jwt, "jwt", type('MockJWT', (), {
        'decode': lambda *args, **kwargs: (_ for _ in ()).throw(JWTError())
    })())
    
    with pytest.raises(HTTPException) as exc:
        decode_access_token("invalid_token")
    assert exc.value.status_code == 401
    assert "Invalid or expired token" in exc.value.detail