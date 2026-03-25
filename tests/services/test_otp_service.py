def test_generate_otp(redis_client):

    from app.services.otp_service import OTPService

    service = OTPService()

    otp = service.generate_otp("phone:999", "fp", "127.0.0.1")

    assert len(otp) == 6

def test_verify_otp_success(redis_client):

    from app.services.otp_service import OTPService

    service = OTPService()

    identifier = "phone:999"

    otp = service.generate_otp(identifier, "fp", "127.0.0.1")

    result = service.verify_otp(identifier, otp, "fp", "127.0.0.1")

    assert result is True

def test_verify_otp_wrong(redis_client):

    from app.services.otp_service import OTPService

    service = OTPService()

    identifier = "phone:999"

    service.generate_otp(identifier, "fp", "127.0.0.1")

    result = service.verify_otp(identifier, "000000", "fp", "127.0.0.1")

    assert result is False

def test_otp_reuse(redis_client):

    from app.services.otp_service import OTPService

    service = OTPService()

    identifier = "phone:999"

    otp = service.generate_otp(identifier, "fp", "127.0.0.1")

    service.verify_otp(identifier, otp, "fp", "127.0.0.1")

    # second use
    result = service.verify_otp(identifier, otp, "fp", "127.0.0.1")

    assert result is False

def test_otp_max_attempts(redis_client):

    from app.services.otp_service import OTPService
    from app.core.config import settings

    service = OTPService()

    identifier = "phone:999"

    service.generate_otp(identifier, "fp", "127.0.0.1")

    for _ in range(settings.OTP_MAX_ATTEMPTS):
        service.verify_otp(identifier, "000000", "fp", "127.0.0.1")

    result = service.verify_otp(identifier, "000000", "fp", "127.0.0.1")

    assert result is False

def test_otp_fingerprint_mismatch(redis_client):

    from app.services.otp_service import OTPService

    service = OTPService()

    identifier = "phone:999"

    otp = service.generate_otp(identifier, "fp1", "127.0.0.1")

    result = service.verify_otp(identifier, otp, "fp2", "127.0.0.1")

    assert result is False