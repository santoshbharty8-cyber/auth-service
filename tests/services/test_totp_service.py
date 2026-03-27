import base64
import pytest
import pyotp

from app.services.totp_service import TOTPService


# ----------------------------------------
# FIXTURE
# ----------------------------------------

@pytest.fixture
def totp_service():
    return TOTPService()


# ----------------------------------------
# TEST: generate_secret
# ----------------------------------------

def test_generate_secret(totp_service):
    secret = totp_service.generate_secret()

    assert isinstance(secret, str)
    assert len(secret) >= 16   # base32 secret length
    assert all(c.isalnum() for c in secret)


# ----------------------------------------
# TEST: build_uri
# ----------------------------------------

def test_build_uri(totp_service):
    import urllib.parse
    import pyotp

    secret = pyotp.random_base32()
    email = "test@example.com"

    uri = totp_service.build_uri(email, secret)

    parsed = urllib.parse.urlparse(uri)
    query = urllib.parse.parse_qs(parsed.query)

    # ✅ correct assertions
    assert parsed.scheme == "otpauth"
    assert parsed.netloc == "totp"   # ✅ FIXED

    decoded_path = urllib.parse.unquote(parsed.path)
    assert email in decoded_path
    assert "AuthSystem" in decoded_path

    assert query["secret"][0] == secret

# ----------------------------------------
# TEST: generate_qr
# ----------------------------------------

def test_generate_qr(totp_service):
    uri = "otpauth://totp/test?secret=ABC123"

    qr_base64 = totp_service.generate_qr(uri)

    # should be valid base64 string
    decoded = base64.b64decode(qr_base64)

    assert isinstance(qr_base64, str)
    assert len(decoded) > 0  # image bytes exist


# ----------------------------------------
# TEST: verify (valid code)
# ----------------------------------------

def test_verify_valid_code(totp_service):
    secret = pyotp.random_base32()

    totp = pyotp.TOTP(secret)
    code = totp.now()

    assert totp_service.verify(secret, code) is True


# ----------------------------------------
# TEST: verify (invalid code)
# ----------------------------------------

def test_verify_invalid_code(totp_service):
    secret = pyotp.random_base32()

    assert totp_service.verify(secret, "000000") is False


def test_totp_generate_and_verify():

    from app.services.totp_service import TOTPService

    service = TOTPService()

    secret = service.generate_secret()

    import pyotp
    code = pyotp.TOTP(secret).now()

    assert service.verify(secret, code) is True


