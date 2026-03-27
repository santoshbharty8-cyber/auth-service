# tests/services/test_recovery_code_service.py

import pytest
from types import SimpleNamespace

from app.services.recovery_code_service import RecoveryCodeService


pytestmark = pytest.mark.usefixtures("reset_modules")

# ---------------------------------------------------
# 🔹 TEST: generate_codes
# ---------------------------------------------------

def test_generate_codes(monkeypatch):

    calls = []

    service = RecoveryCodeService(None)

    # ✅ force repo
    service.recovery_code_repo = SimpleNamespace(
        create=lambda code: calls.append(code)
    )

    # deterministic token
    monkeypatch.setattr(
        "app.services.recovery_code_service.secrets.token_hex",
        lambda n: "abcd1234"
    )

    # deterministic hash
    monkeypatch.setattr(service, "_hash", lambda x: "hashed")

    codes = service.generate_codes("user1")

    assert len(codes) == 10
    assert all(code == "ABCD-1234" for code in codes)
    assert len(calls) == 10


# ---------------------------------------------------
# 🔹 TEST: verify_code SUCCESS
# ---------------------------------------------------

def test_verify_code_success():

    from app.services.recovery_code_service import RecoveryCodeService

    calls = {"marked": False}

    fake_recovery = object()

    repo = type("Repo", (), {
        "find_valid_code": lambda *a, **k: fake_recovery,  # ✅ simulate valid code
        "mark_used": lambda *a, **k: calls.update({"marked": True})
    })()

    service = RecoveryCodeService(repo)

    result = service.verify_code("user1", "VALID-CODE")

    assert result is True
    assert calls["marked"] is True

# ---------------------------------------------------
# 🔹 TEST: verify_code INVALID (missing branch)
# ---------------------------------------------------

def test_verify_code_invalid():

    from app.services.recovery_code_service import RecoveryCodeService

    calls = {"marked": False}

    repo = type("Repo", (), {
        "find_valid_code": lambda *a, **k: None,
        "mark_used": lambda *a, **k: calls.update({"marked": True})
    })()

    service = RecoveryCodeService(repo)

    result = service.verify_code("user1", "INVALID")

    assert result is False
    assert calls["marked"] is False

# ---------------------------------------------------
# 🔹 TEST: _hash function
# ---------------------------------------------------

def test_hash_function():

    service = RecoveryCodeService(None)

    result = service._hash("test")

    assert isinstance(result, str)
    assert len(result) == 64  # sha256 hex