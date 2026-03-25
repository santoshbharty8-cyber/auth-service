def test_totp_generate_and_verify():

    from app.services.totp_service import TOTPService

    service = TOTPService()

    secret = service.generate_secret()

    import pyotp
    code = pyotp.TOTP(secret).now()

    assert service.verify(secret, code) is True
