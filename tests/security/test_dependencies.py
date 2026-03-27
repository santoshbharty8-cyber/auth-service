from types import SimpleNamespace
from fastapi import HTTPException
import pytest

from app.security.dependencies import get_current_user

def test_get_current_user_missing_user_id(monkeypatch):

    monkeypatch.setattr(
        "app.security.dependencies.verify_access_token",
        lambda x: {"ver": 1}  # no "sub"
    )

    request = SimpleNamespace(state=SimpleNamespace())

    with pytest.raises(HTTPException) as exc:
        get_current_user(
            request,
            credentials=SimpleNamespace(credentials="token"),
            db=None
        )

    assert exc.value.status_code == 401

def test_get_current_user_invalid_uuid(monkeypatch):

    monkeypatch.setattr(
        "app.security.dependencies.verify_access_token",
        lambda x: {"sub": "not-a-uuid", "ver": 1}
    )

    request = SimpleNamespace(state=SimpleNamespace())

    with pytest.raises(HTTPException) as exc:
        get_current_user(
            request,
            credentials=SimpleNamespace(credentials="token"),
            db=None
        )

    assert "Invalid user ID format" in str(exc.value.detail)

def test_get_current_user_user_not_found(monkeypatch):

    monkeypatch.setattr(
        "app.security.dependencies.verify_access_token",
        lambda x: {"sub": "123e4567-e89b-12d3-a456-426614174000", "ver": 1}
    )

    monkeypatch.setattr(
        "app.security.dependencies.UserRepository",
        lambda db: SimpleNamespace(find_by_id=lambda x: None)
    )

    request = SimpleNamespace(state=SimpleNamespace())

    with pytest.raises(HTTPException):
        get_current_user(
            request,
            credentials=SimpleNamespace(credentials="token"),
            db=None
        )

def test_get_current_user_token_version_mismatch(monkeypatch):

    monkeypatch.setattr(
        "app.security.dependencies.verify_access_token",
        lambda x: {"sub": "123e4567-e89b-12d3-a456-426614174000", "ver": 2}
    )

    fake_user = SimpleNamespace(token_version=1)

    monkeypatch.setattr(
        "app.security.dependencies.UserRepository",
        lambda db: SimpleNamespace(find_by_id=lambda x: fake_user)
    )

    request = SimpleNamespace(state=SimpleNamespace())

    with pytest.raises(HTTPException) as exc:
        get_current_user(
            request,
            credentials=SimpleNamespace(credentials="token"),
            db=None
        )

    assert "Session invalidated" in str(exc.value.detail)

def test_get_current_user_success(monkeypatch):

    monkeypatch.setattr(
        "app.security.dependencies.verify_access_token",
        lambda x: {"sub": "123e4567-e89b-12d3-a456-426614174000", "ver": 1}
    )

    fake_user = SimpleNamespace(token_version=1)

    monkeypatch.setattr(
        "app.security.dependencies.UserRepository",
        lambda db: SimpleNamespace(find_by_id=lambda x: fake_user)
    )

    request = SimpleNamespace(state=SimpleNamespace())

    result = get_current_user(
        request,
        credentials=SimpleNamespace(credentials="token"),
        db=None
    )

    assert result == fake_user
    assert request.state.user_id == "123e4567-e89b-12d3-a456-426614174000"