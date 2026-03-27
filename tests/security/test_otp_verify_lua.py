from app.security.otp_verify_lua import OTP_VERIFY_LUA


def test_otp_verify_lua_defined():
    assert isinstance(OTP_VERIFY_LUA, str)
    assert len(OTP_VERIFY_LUA) > 0
    assert "local otp_key" in OTP_VERIFY_LUA